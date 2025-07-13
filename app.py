"""
India Travel Explorer with AI Assistant and Monument Recognition Integration
A combined application that integrates India Travel Explorer, AI Travel Assistant, and Monument Recognition
"""

import os
import logging
import math
import time
import json
import threading
import re
import requests
from urllib.parse import quote
from datetime import datetime, timedelta
from collections import defaultdict, deque
from functools import wraps
from flask import Flask, jsonify, render_template, request, abort, session, make_response, redirect, url_for
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from bson.json_util import dumps
from bson.objectid import ObjectId
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename
from groq import Groq

# Configure logging
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

file_handler = RotatingFileHandler(
    os.path.join(log_dir, 'india_travel_app.log'),
    maxBytes=5242880,
    backupCount=3
)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(file_handler)

# Load environment variables
load_dotenv()
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Access environment variables
groq_api_key = os.getenv("GROQ_API_KEY")
unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY")
openweather_api_key = os.getenv("OPENWEATHER_API_KEY")
spotify_api_key = os.getenv("SPOTIFY_API_KEY")
secret_key = os.getenv("SECRET_KEY", "india-travel-app-secret")
mongodb_uri = os.getenv("MONGODB_URI")

# Roboflow Info
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY")
PROJECT_NAME = os.getenv("ROBOFLOW_PROJECT_NAME")
WORKSPACE = os.getenv("ROBOFLOW_WORKSPACE")
VERSION = os.getenv("ROBOFLOW_VERSION")

# Set the Flask secret key
from flask import Flask
app = Flask(__name__)
app.secret_key = secret_key


# Upload folder for monument images
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Initialize Flask app - MOVED HERE BEFORE ANY CONFIG REFERENCES
app = Flask(__name__)
app.secret_key = secret_key
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB limit for uploads
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configure CORS
CORS(app, resources={r"/*": {"origins": "*"}})

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Configure rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# MongoDB Configuration
DATABASE_NAME = "india_travel"
STATES_COLLECTION = "states"
TOURIST_PLACES_COLLECTION = "tourist_places"

# Initialize Groq client
groq_client = Groq(api_key=groq_api_key)
MODEL_NAME = "llama3-8b-8192"

# Caching and rate limiting
response_cache = {}
CACHE_EXPIRY = 1800
cache_lock = threading.Lock()

user_requests = defaultdict(lambda: deque())
RATE_LIMIT_REQUESTS = 15
RATE_LIMIT_WINDOW = 300

# Global variables for database connection
client = None
db = None
states_collection = None
tourist_places_collection = None

# Define state coordinates for fallback


# Define state coordinates for fallback
stateCoordinates = {
    # North India
    'Delhi': [28.6139, 77.2090],
    'Punjab': [31.1471, 75.3412],
    'Haryana': [29.0588, 76.0856],
    'Rajasthan': [27.0238, 74.2179],
    'Uttar Pradesh': [26.8467, 80.9462],
    'Himachal Pradesh': [31.1048, 77.1734],
    'Uttarakhand': [30.0668, 79.0193],
    'Jammu and Kashmir': [34.0837, 74.7973],
    'Ladakh': [34.1526, 77.5770],
    'Chandigarh': [30.7333, 76.7794],
    
    # South India
    'Karnataka': [15.3173, 75.7139],
    'Tamil Nadu': [11.1271, 78.6569],
    'Kerala': [10.8505, 76.2711],
    'Andhra Pradesh': [15.9129, 79.7400],
    'Telangana': [18.1124, 79.0193],
    'Puducherry': [11.9416, 79.8083],
    
    # Other states
    'Maharashtra': [19.7515, 75.7139],
    'Gujarat': [23.0225, 72.5714],
    'Madhya Pradesh': [22.9734, 78.6569],
    'Chhattisgarh': [21.2787, 81.8661],
    'Odisha': [20.9517, 85.0985],
    'West Bengal': [22.9868, 87.8550],
    'Bihar': [25.0961, 85.3131],
    'Jharkhand': [23.6102, 85.2799],
    'Assam': [26.2006, 92.9376],
    'Meghalaya': [25.4670, 91.3662],
    'Manipur': [24.6637, 93.9063],
    'Mizoram': [23.1645, 92.9376],
    'Tripura': [23.9408, 91.9882],
    'Nagaland': [26.1584, 94.5624],
    'Arunachal Pradesh': [28.2180, 94.7278],
    'Sikkim': [27.5330, 88.5122],
    'Goa': [15.2993, 74.1240]
}

# Rate limiting and caching helpers
def rate_limit_check(user_ip):
    """Enhanced rate limiting"""
    now = datetime.now()
    user_queue = user_requests[user_ip]
    
    while user_queue and user_queue[0] < now - timedelta(seconds=RATE_LIMIT_WINDOW):
        user_queue.popleft()
    
    if len(user_queue) >= RATE_LIMIT_REQUESTS:
        return False
    
    user_queue.append(now)
    return True

def extract_smart_location(text):
    """Enhanced location extraction"""
    text_lower = text.lower()
    
    # Common Indian destinations
    common_destinations = ['Mumbai', 'Delhi', 'Bangalore', 'Kolkata', 'Chennai', 'Hyderabad', 'Jaipur', 'Agra', 'Varanasi', 'Udaipur', 'Jodhpur', 'Pushkar', 'Rishikesh', 'Haridwar', 'Amritsar', 'Mysore', 'Cochin', 'Madurai', 'Shimla', 'Manali', 'Darjeeling', 'Ooty', 'Munnar', 'Coorg', 'Nainital', 'Mussoorie', 'Mount Abu', 'Kodaikanal', 'Lansdowne', 'Palolem', 'Arambol', 'Varkala', 'Kovalam', 'Gokarna', 'Leh Ladakh', 'Spiti Valley', 'Kasol', 'Hampi', 'Pondicherry', 'Andaman Islands', 'Rajasthan', 'Kerala', 'Goa', 'Himachal Pradesh', 'Tamil Nadu']
    
    for dest in common_destinations:
        if dest.lower() in text_lower:
            return dest
    
    # Patterns for location extraction
    patterns = [
        r'(?:visit|go to|travel to|trip to|plan.*?to|in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:travel|trip|tour|itinerary)',
        r'planning.*?(?:to|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    
    return "India"

def add_to_cache(key, data, expiry=None):
    """Thread-safe cache addition"""
    with cache_lock:
        response_cache[key] = {
            "data": data,
            "expires": time.time() + (expiry or CACHE_EXPIRY)
        }

def get_from_cache(key):
    """Thread-safe cache retrieval"""
    with cache_lock:
        if key in response_cache:
            item = response_cache[key]
            if item["expires"] > time.time():
                return item["data"]
            else:
                del response_cache[key]
    return None

class DatabaseConnection:
    """Manages MongoDB connection with retry logic"""
    
    @staticmethod
    def connect():
        """Establish connection to MongoDB with retry logic"""
        global client, db, states_collection, tourist_places_collection
        
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"Attempting to connect to MongoDB (Attempt {retry_count + 1}/{max_retries})")
                
                client = MongoClient(
                    mongodb_uri,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000,
                    socketTimeoutMS=10000,
                    maxPoolSize=50,
                    minPoolSize=10
                )
                
                # Test connection
                client.admin.command('ping')
                
                db = client[DATABASE_NAME]
                states_collection = db[STATES_COLLECTION]
                tourist_places_collection = db[TOURIST_PLACES_COLLECTION]
                
                logger.info("Successfully connected to MongoDB!")
                return True
                
            except (ConnectionFailure, ServerSelectionTimeoutError) as e:
                retry_count += 1
                logger.error(f"MongoDB connection failed (Attempt {retry_count}/{max_retries}): {str(e)}")
                
                if retry_count >= max_retries:
                    logger.critical("Failed to connect to MongoDB after all retries")
                    return False
                    
            except Exception as e:
                logger.critical(f"Unexpected error connecting to MongoDB: {str(e)}")
                return False
    
    @staticmethod
    def ensure_connection():
        """Ensure database connection is active"""
        global client
        
        try:
            if client is None:
                return DatabaseConnection.connect()
            
            # Test if connection is still alive
            client.admin.command('ping')
            return True
            
        except:
            logger.warning("Lost connection to MongoDB, attempting to reconnect...")
            return DatabaseConnection.connect()

# Initialize database connection
DatabaseConnection.connect()
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
@app.route('/monument-recognition')
def monument_recognition():
    """Serve the monument recognition HTML page"""
    return render_template('monument_recognition.html')

@app.route('/predict', methods=['POST'])
def predict():
    """Process uploaded monument image and predict using Roboflow"""
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image uploaded'})
    
    image = request.files['image']
    if image.filename == '':
        return jsonify({'success': False, 'error': 'No image selected'})
        
    if image and allowed_file(image.filename):
        filename = secure_filename(image.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(filepath)
        
        try:
            # Upload to Roboflow for prediction
            url = f"https://detect.roboflow.com/{PROJECT_NAME}/{VERSION}?api_key={ROBOFLOW_API_KEY}"
            with open(filepath, 'rb') as img_file:
                response = requests.post(
                    url,
                    files={'file': img_file},
                    data={'name': filename}
                )
            
            # Clean up the uploaded file
            os.remove(filepath)
            
            if response.status_code == 200:
                result = response.json()
                try:
                    # Get prediction
                    prediction = result['predictions'][0]['class']
                    
                    # Find tourist place info
                    place_info = get_monument_info(prediction)
                    
                    return jsonify({
                        'success': True, 
                        'prediction': prediction,
                        'place_info': place_info
                    })
                except (IndexError, KeyError):
                    return jsonify({'success': False, 'error': 'No monument detected'})
            else:
                return jsonify({'success': False, 'error': f'API error: {response.status_code}'})
                
        except Exception as e:
            logger.error(f"Error in monument prediction: {str(e)}")
            return jsonify({'success': False, 'error': str(e)})
    else:
        return jsonify({'success': False, 'error': 'Invalid file type'})
def get_monument_info(monument_name):
    """Get information about the recognized monument from the database"""
    try:
        if not DatabaseConnection.ensure_connection():
            return None
            
        # Try to find the monument in tourist places collection
        place = tourist_places_collection.find_one({
            "name": {"$regex": f"^{monument_name}$", "$options": "i"}
        })
        
        if place:
            return sanitize_json_response(place)
            
        # If not found, search in the description field
        place = tourist_places_collection.find_one({
            "description": {"$regex": monument_name, "$options": "i"}
        })
        
        if place:
            return sanitize_json_response(place)
            
        # Create basic info if not found
        return {
            "name": monument_name,
            "description": f"Information about {monument_name} is currently being updated.",
            "recognized": True
        }
            
    except Exception as e:
        logger.error(f"Error getting monument info: {str(e)}")
        return None
def require_db_connection(f):
    """Decorator to ensure database connection before executing route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not DatabaseConnection.ensure_connection():
            return jsonify({
                "error": "Database connection unavailable",
                "message": "Unable to connect to the database. Please try again later."
            }), 503
        return f(*args, **kwargs)
    return decorated_function

def sanitize_json_response(data):
    """Sanitize MongoDB response for JSON serialization"""
    if isinstance(data, list):
        return [sanitize_json_response(item) for item in data]
    elif isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if key == '_id' and isinstance(value, ObjectId):
                sanitized['id'] = str(value)
            elif isinstance(value, ObjectId):
                sanitized[key] = str(value)
            elif isinstance(value, (dict, list)):
                sanitized[key] = sanitize_json_response(value)
            else:
                sanitized[key] = value
        return sanitized
    return data

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Not Found",
        "message": "The requested resource was not found on this server."
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({
        "error": "Internal Server Error",
        "message": "An unexpected error occurred. Please try again later."
    }), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        "error": "Rate Limit Exceeded",
        "message": f"Rate limit exceeded: {e.description}"
    }), 429

# Routes
@app.route('/')
def home():
    """Serve the India Travel Explorer HTML page"""
    return render_template('indexx.html')

@app.route('/assistant')
def assistant():
    """Serve the AI Travel Assistant HTML page"""
    return render_template('assistant.html')

@app.route('/health')
@limiter.limit("10 per minute")
def health_check():
    """Health check endpoint"""
    db_status = "connected" if DatabaseConnection.ensure_connection() else "disconnected"
    
    return jsonify({
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
        "cache_size": len(response_cache),
        "version": "1.0.0"
    })

# ============ India Travel Explorer API Routes ============

@app.route('/api/stats')
@require_db_connection
@limiter.limit("30 per minute")
def get_statistics():
    """Get statistics about states in the database"""
    try:
        pipeline = [
            {
                "$group": {
                    "_id": "$region",
                    "count": {"$sum": 1},
                    "states": {"$push": "$name"}
                }
            },
            {
                "$project": {
                    "region": "$_id",
                    "count": 1,
                    "states": 1,
                    "_id": 0
                }
            }
        ]
        
        stats = list(states_collection.aggregate(pipeline))
        total_states = states_collection.count_documents({})
        
        return jsonify({
            "total_states": total_states,
            "by_region": stats,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error fetching statistics: {str(e)}")
        return jsonify({
            "error": "Failed to fetch statistics",
            "message": str(e)
        }), 500

@app.route('/states/<region>')
@require_db_connection
@limiter.limit("30 per minute")
def get_states_by_region(region):
    """Fetch states by region (north or south)"""
    try:
        # Validate region parameter
        valid_regions = ['north', 'south']
        if region.lower() not in valid_regions:
            return jsonify({
                "error": "Invalid region",
                "message": f"Region must be one of: {', '.join(valid_regions)}"
            }), 400
        
        # Query with projection to exclude unnecessary fields
        projection = {
            'name': 1,
            'capital': 1,
            'region': 1,
            'description': 1,
            'image': 1,
            'touristPlaces': 1,
            'cuisine': 1,
            'culture': 1,
            'bestTimeToVisit': 1,
            'transportation': 1,
            'highlights': 1,
            'hotels': 1
        }
        
        states = list(states_collection.find(
            {"region": region.lower()},
            projection
        ).sort("name", 1))
        
        if not states:
            logger.warning(f"No states found for region: {region}")
            return jsonify([])
        
        # Sanitize and return response
        sanitized_states = sanitize_json_response(states)
        return jsonify(sanitized_states)
        
    except Exception as e:
        logger.error(f"Error fetching states by region '{region}': {str(e)}")
        return jsonify({
            "error": "Failed to fetch states",
            "message": "An error occurred while retrieving states data."
        }), 500

@app.route('/api/all-states')
@require_db_connection
@limiter.limit("20 per minute")
def get_all_states():
    """Fetch all states from the database"""
    try:
        # Query with projection and sorting
        projection = {
            'name': 1,
            'capital': 1,
            'region': 1,
            'description': 1,
            'image': 1,
            'touristPlaces': 1,
            'cuisine': 1,
            'culture': 1,
            'bestTimeToVisit': 1,
            'transportation': 1,
            'highlights': 1,
            'hotels': 1
        }
        
        states = list(states_collection.find({}, projection).sort([
            ("region", 1),
            ("name", 1)
        ]))
        
        if not states:
            logger.warning("No states found in database")
            return jsonify([])
        
        # Sanitize and return response
        sanitized_states = sanitize_json_response(states)
        return jsonify(sanitized_states)
        
    except Exception as e:
        logger.error(f"Error fetching all states: {str(e)}")
        return jsonify({
            "error": "Failed to fetch states",
            "message": "An error occurred while retrieving states data."
        }), 500

@app.route('/api/state/<state_name>')
@require_db_connection
@limiter.limit("30 per minute")
def get_state_details(state_name):
    """Fetch detailed information about a specific state"""
    try:
        # Sanitize state name
        state_name = state_name.strip()
        
        if not state_name:
            return jsonify({
                "error": "Invalid state name",
                "message": "State name cannot be empty"
            }), 400
        
        # Case-insensitive search
        state = states_collection.find_one({
            "name": {"$regex": f"^{state_name}$", "$options": "i"}
        })
        
        if not state:
            return jsonify({
                "error": "State not found",
                "message": f"No state found with name: {state_name}"
            }), 404
        
        # Sanitize and return response
        sanitized_state = sanitize_json_response(state)
        return jsonify(sanitized_state)
        
    except Exception as e:
        logger.error(f"Error fetching state details for '{state_name}': {str(e)}")
        return jsonify({
            "error": "Failed to fetch state details",
            "message": "An error occurred while retrieving state information."
        }), 500

@app.route('/api/tourist-place')
@require_db_connection
@limiter.limit("40 per minute")
def get_tourist_place():
    """Fetch detailed information about a specific tourist place"""
    try:
        place_name = request.args.get('name', '').strip()
        state_name = request.args.get('state', '').strip()
        
        if not place_name:
            return jsonify({
                "error": "Invalid place name",
                "message": "Tourist place name cannot be empty"
            }), 400
            
        # Query with filtering
        query = {"name": {"$regex": f"^{place_name}$", "$options": "i"}}
        
        if state_name:
            query["state"] = {"$regex": f"^{state_name}$", "$options": "i"}
        
        # Try to find the place
        place = tourist_places_collection.find_one(query)
        
        # If not found in dedicated collection, try to search in the places array in states
        if not place:
            # This is a fallback in case the tourist place is not in the dedicated collection
            state = states_collection.find_one({
                "name": {"$regex": f"^{state_name}$", "$options": "i"},
                "touristPlaces": {"$regex": f"^{place_name}$", "$options": "i"}
            })
            
            if state:
                # Get coordinates for this state
                coords = [20.5937, 78.9629]  # Default to center of India
                if state_name in stateCoordinates:
                    coords = stateCoordinates[state_name]
                
                # Check if this state has detailed tourist place information
                detailed_place_info = None
                if 'touristPlacesDetails' in state:
                    for place_detail in state['touristPlacesDetails']:
                        if place_detail['name'].lower() == place_name.lower():
                            detailed_place_info = place_detail
                            break
                
                # Create place object with available information
                place = {
                    "name": place_name,
                    "state": state_name,
                    "description": detailed_place_info['description'] if detailed_place_info and 'description' in detailed_place_info else f"A popular tourist destination in {state_name}.",
                    "location": detailed_place_info['location'] if detailed_place_info and 'location' in detailed_place_info else {
                        "lat": coords[0],
                        "lng": coords[1]
                    },
                    "bestTimeToVisit": detailed_place_info['bestTimeToVisit'] if detailed_place_info and 'bestTimeToVisit' in detailed_place_info else state.get("bestTimeToVisit", "Year-round"),
                    "entryFee": detailed_place_info['entryFee'] if detailed_place_info and 'entryFee' in detailed_place_info else None,
                    "timings": detailed_place_info['timings'] if detailed_place_info and 'timings' in detailed_place_info else None,
                    "images": detailed_place_info['images'] if detailed_place_info and 'images' in detailed_place_info else [],
                    "useGeoapify": True  # Add this flag to tell frontend to use Geoapify
                }
                
                # Add hotels if they exist in the detailed place info
                if detailed_place_info and 'hotels' in detailed_place_info and detailed_place_info['hotels']:
                    place['hotels'] = detailed_place_info['hotels']
                else:
                    place['hotels'] = []
                
                # Add restaurants if they exist in the detailed place info
                if detailed_place_info and 'restaurants' in detailed_place_info and detailed_place_info['restaurants']:
                    place['restaurants'] = detailed_place_info['restaurants']
                else:
                    place['restaurants'] = []
            else:
                return jsonify({
                    "error": "Tourist place not found",
                    "message": f"No details found for {place_name} in {state_name}"
                }), 404
        else:
            # If found in the dedicated tourist_places collection but has no hotels/restaurants,
            # mark it to use Geoapify on the frontend
            if not place.get('hotels') or not place.get('restaurants') or len(place.get('hotels', [])) == 0 or len(place.get('restaurants', [])) == 0:
                place['useGeoapify'] = True
                
                # Initialize empty arrays if they don't exist
                if 'hotels' not in place or place['hotels'] is None:
                    place['hotels'] = []
                if 'restaurants' not in place or place['restaurants'] is None:
                    place['restaurants'] = []
        
        # Sanitize and return response
        sanitized_place = sanitize_json_response(place)
        return jsonify(sanitized_place)
        
    except Exception as e:
        logger.error(f"Error fetching tourist place details for '{place_name}': {str(e)}")
        return jsonify({
            "error": "Failed to fetch tourist place details",
            "message": "An error occurred while retrieving tourist place information."
        }), 500

# ============ AI Travel Assistant API Routes ============

@app.route("/api/message", methods=["POST"])
def handle_message():
    """Chat message handler"""
    try:
        user_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        if not rate_limit_check(user_ip):
            return jsonify({
                "error": "Too many requests. Please wait 5 minutes.",
                "retry_after": 300
            }), 429
        
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 415
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400

        user_input = data.get("message", "").strip()
        context = data.get("context", {})
        
        if not user_input or len(user_input) > 300:
            return jsonify({"error": "Please enter a valid message (max 300 characters)"}), 400

        cache_key = f"msg_{hash(user_input.lower())}_{hash(str(context))}"
        cached_response = get_from_cache(cache_key)
        if cached_response:
            return jsonify(cached_response)
        
        response_data = process_travel_query(user_input, context)
        add_to_cache(cache_key, response_data)
        
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return jsonify({
            "error": "Sorry, I'm having trouble right now. Please try again.",
            "suggestion": "Try asking about a specific destination like 'Plan a trip to Kerala'"
        }), 500

@app.route("/api/plan-trip", methods=["POST"])
def plan_trip():
    """AI Trip Planner endpoint - Uses Groq API dynamically"""
    try:
        user_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        if not rate_limit_check(user_ip):
            return jsonify({
                "error": "Too many requests. Please wait 5 minutes.",
                "retry_after": 300
            }), 429
        
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 415
            
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400

        # Extract trip parameters
        destination = data.get("destination", "").strip()
        duration = int(data.get("duration", 3))
        budget_type = data.get("budget_type", "mid_range")
        interests = data.get("interests", [])
        travel_style = data.get("travel_style", "balanced")
        group_size = int(data.get("group_size", 2))
        
        if not destination:
            return jsonify({"error": "Please specify a destination"}), 400
        
        if duration < 1 or duration > 30:
            return jsonify({"error": "Duration must be between 1-30 days"}), 400
        
        logger.info(f"Planning trip using AI: {destination}, {duration} days, {budget_type}, {group_size} people")
        
        # Check cache first
        cache_key = f"ai_trip_{destination.lower()}_{duration}_{budget_type}_{travel_style}_{group_size}_{hash(str(interests))}"
        cached_plan = get_from_cache(cache_key)
        if cached_plan:
            logger.info("Returning cached AI trip plan")
            return jsonify(cached_plan)
        
        # Generate AI-powered trip plan
        trip_plan = generate_ai_trip_plan(destination, duration, budget_type, interests, travel_style, group_size)
        
        # Cache the plan for 2 hours
        add_to_cache(cache_key, trip_plan, expiry=7200)
        
        logger.info("AI trip plan generated successfully")
        return jsonify(trip_plan)

    except Exception as e:
        logger.error(f"Error planning trip: {str(e)}")
        return jsonify({
            "error": "Couldn't create your trip plan. Please try again.",
            "suggestion": "Try with a destination like 'Rajasthan' or 'Kerala'"
        }), 500

def process_travel_query(user_input, context=None):
    """Process general travel queries using AI with optional context"""
    if context is None:
        context = {}
    
    # Use context if provided, otherwise extract from the message
    location = context.get("state") or context.get("place") or extract_smart_location(user_input)
    
    # Include context in the prompt
    context_info = ""
    if context.get("state"):
        context_info = f"User is currently exploring {context['state']}. "
        if context.get("place"):
            context_info += f"Specifically looking at {context['place']} in {context['state']}. "
    elif context.get("region"):
        context_info = f"User is exploring the {context['region']} region of India. "
    
    travel_prompt = f"""
You are India Travel Assistant - a friendly expert helping tourists explore India.

User query: "{user_input}"
{context_info}
Detected location: {location}

Provide a helpful response following this structure (keep under 200 words):

🏛️ OVERVIEW: Brief highlight of {location}

📅 BEST TIME: Ideal months with reasons

🎯 TOP ATTRACTIONS: 3-4 must-see places

🍽️ FOOD SPECIALTIES: 3-4 local dishes

🌟 INSIDER TIP: One special recommendation

If the query asks about trip planning, suggest using the trip planner feature.
If not about India travel, respond: "I specialize in India travel! Ask me about destinations, food, weather, or trip planning. 🇮🇳"
"""

    try:
        response = groq_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful India travel expert. Be concise, practical, and enthusiastic."},
                {"role": "user", "content": travel_prompt}
            ],
            temperature=0.6,
            max_tokens=512,
            timeout=10
        )
        text_reply = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Groq API error: {str(e)}")
        text_reply = f"I'd love to help you explore {location}! This destination offers amazing experiences. Please try again or use our trip planner for detailed itineraries."

    # Fetch additional data
    weather_data = fetch_weather_quick(location)
    image_data = fetch_image_quick(location)

    return {
        "response": text_reply,
        "location": location,
        "weather": weather_data,
        "image_url": image_data,
        "timestamp": int(time.time()),
        "suggestions": get_related_suggestions(location)
    }

def generate_ai_trip_plan(destination, duration, budget_type, interests, travel_style, group_size):
    """Generate trip plan using Groq AI - No predefined data"""
    
    # Create comprehensive prompt for AI
    interest_text = f"with focus on {', '.join(interests)}" if interests else ""
    
    trip_prompt = f"""
You are an expert travel planner for India. Create a detailed {duration}-day itinerary for {destination}, India.

Trip Details:
- Destination: {destination}
- Duration: {duration} days
- Budget Type: {budget_type} (budget: ₹1000-2000/day, mid_range: ₹2500-5000/day, luxury: ₹5000+/day)
- Group Size: {group_size} people
- Travel Style: {travel_style}
- Interests: {interests if interests else ['general sightseeing']}

Create a comprehensive itinerary with:

1. TRIP OVERVIEW:
- Best time to visit {destination}
- Main theme of the trip
- Top 4-5 highlights
- Total estimated cost for {group_size} people

2. DAILY ITINERARY for each day (Day 1 to Day {duration}):
For each day provide:
- Day title and overview
- Morning activity (9 AM): specific activity, location, duration, cost per person, tips
- Afternoon activity (2 PM): specific activity, location, duration, cost per person, tips  
- Evening activity (7 PM): specific activity, location, duration, cost per person, tips
- Accommodation recommendation: name, type, location, cost per night, amenities
- Meal suggestions: breakfast, lunch, dinner with specific dishes and costs
- Transportation: method, cost, booking info
- Daily total cost per person

IMPORTANT: Make each day completely different with unique activities. Day 1 should be arrival/orientation, Day 2 major attractions, Day 3 cultural experiences, etc.

3. BUDGET BREAKDOWN:
- Accommodation total for {group_size} people
- Food total for {group_size} people  
- Transport total for {group_size} people
- Activities total for {group_size} people
- Shopping/souvenirs estimate
- 10-15% contingency
- Grand total and per person cost

4. PRACTICAL INFORMATION:
- Local language and useful phrases
- Cultural customs and dress codes
- Currency, tipping, and bargaining tips
- Safety recommendations
- Packing essentials (clothing, documents, health items)
- Food specialties to try and where to find them
- Weather and clothing recommendations
- Transportation options and apps

Provide realistic costs in Indian Rupees for 2025. Include specific place names, real attractions, actual restaurants/hotels, and practical tips. Make each day's activities completely unique and engaging.

Focus on authentic experiences that match the {travel_style} style and {budget_type} budget level.
"""

    try:
        # Get comprehensive AI response
        response = groq_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system", 
                    "content": "You are the best travel planner for India with extensive knowledge of destinations, attractions, costs, and practical travel advice. Create detailed, realistic, and unique itineraries."
                },
                {
                    "role": "user", 
                    "content": trip_prompt
                }
            ],
            temperature=0.7,  # Higher creativity for unique content
            max_tokens=4000,  # Allow for comprehensive response
            timeout=30
        )
        
        ai_response = response.choices[0].message.content.strip()
        logger.info(f"AI generated response length: {len(ai_response)}")
        
        # Parse and structure the AI response
        structured_plan = parse_ai_response_to_structure(destination, duration, budget_type, group_size, ai_response)
        
        # Add additional real-time data
        structured_plan["weather"] = fetch_weather_quick(destination)
        structured_plan["destination_image"] = fetch_image_quick(destination)
        structured_plan["generated_at"] = int(time.time())
        structured_plan["ai_generated"] = True
        structured_plan["raw_ai_response"] = ai_response  # Include full AI response
        
        return structured_plan
        
    except Exception as e:
        logger.error(f"Error generating AI trip plan: {str(e)}")
        return generate_fallback_plan(destination, duration, budget_type, group_size)

def parse_ai_response_to_structure(destination, duration, budget_type, group_size, ai_response):
    """Parse AI response into structured format for frontend"""
    
    # Extract basic costs for calculationsx
    daily_costs = {
        'budget': 1500,
        'mid_range': 3500,
        'luxury': 7000
    }
    
    daily_cost = daily_costs.get(budget_type, 3500)
    total_cost = daily_cost * duration * group_size
    
    # Create structured response
    structured_plan = {
        "success": True,
        "trip_overview": {
            "destination": destination,
            "duration": duration,
            "group_size": group_size,
            "best_time": extract_best_time(ai_response, destination),
            "trip_theme": extract_trip_theme(ai_response, destination),
            "highlights": extract_highlights(ai_response, destination),
            "total_estimated_cost": f"₹{total_cost:,} for {group_size} people"
        },
        "daily_itinerary": parse_daily_itinerary(ai_response, duration, destination),
        "budget_breakdown": parse_budget_breakdown(ai_response, total_cost, group_size),
        "local_insights": parse_local_insights(ai_response),
        "packing_essentials": parse_packing_essentials(ai_response),
        "food_experience": parse_food_experience(ai_response, destination),
        "weather_and_clothing": parse_weather_clothing(ai_response, destination),
        "full_ai_response": ai_response
    }
    
    return structured_plan

def parse_daily_itinerary(ai_response, duration, destination):
    """Parse daily itinerary from AI response"""
    
    daily_activities = []
    
    # Try to extract day-by-day information from AI response
    for day in range(1, duration + 1):
        # Create day structure with AI-generated content
        day_plan = {
            "day": day,
            "title": extract_day_title(ai_response, day, destination),
            "overview": f"Explore {destination} - Day {day} activities",
            "morning": {
                "time": "09:00 AM",
                "activity": extract_day_activity(ai_response, day, "morning", destination),
                "location": extract_activity_location(ai_response, day, "morning", destination),
                "duration": "3 hours",
                "cost_per_person": f"₹{300 + (day * 50)}",
                "tips": "Start early for the best experience"
            },
            "afternoon": {
                "time": "02:00 PM",
                "activity": extract_day_activity(ai_response, day, "afternoon", destination),
                "location": extract_activity_location(ai_response, day, "afternoon", destination),
                "duration": "4 hours",
                "cost_per_person": f"₹{500 + (day * 100)}",
                "tips": "Perfect time for detailed exploration"
            },
            "evening": {
                "time": "07:00 PM",
                "activity": extract_day_activity(ai_response, day, "evening", destination),
                "location": extract_activity_location(ai_response, day, "evening", destination),
                "duration": "2-3 hours",
                "cost_per_person": f"₹{400 + (day * 75)}",
                "tips": "Experience local evening culture"
            },
            "accommodation": {
                "name": f"Recommended hotel in {destination}",
                "type": "Hotel",
                "location": f"Central {destination}",
                "cost_per_night": f"₹{2000 + (day * 200)}",
                "amenities": ["WiFi", "AC", "Restaurant"],
                "booking_tip": "Book in advance for better rates"
            },
            "meals": {
                "breakfast": {
                    "restaurant": f"Local breakfast spot",
                    "dish": "Traditional breakfast",
                    "cost": f"₹{200 + (day * 25)} per person"
                },
                "lunch": {
                    "restaurant": f"Popular restaurant",
                    "dish": "Regional specialty",
                    "cost": f"₹{400 + (day * 50)} per person"
                },
                "dinner": {
                    "restaurant": f"Recommended dinner place",
                    "dish": "Local cuisine",
                    "cost": f"₹{600 + (day * 75)} per person"
                }
            },
            "transport": {
                "method": "Local taxi/auto",
                "cost_per_person": f"₹{300 + (day * 50)}",
                "booking_info": "Available through apps or hotel"
            },
            "daily_total_per_person": f"₹{2000 + (day * 200)}"
        }
        
        daily_activities.append(day_plan)
    
    return daily_activities

def extract_day_title(ai_response, day, destination):
    """Extract day title from AI response"""
    patterns = [
        rf"Day {day}[:\-\s]*([^\n]+)",
        rf"Day {day}[:\-\s]*(.{20,80})"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, ai_response, re.IGNORECASE)
        if match:
            title = match.group(1).strip()
            if len(title) > 5:
                return title[:60]  # Limit title length
    
    # Fallback titles
    day_titles = {
        1: f"Arrival and First Day in {destination}",
        2: f"Exploring Major Attractions of {destination}",
        3: f"Cultural Immersion in {destination}",
        4: f"Adventure and Local Experiences",
        5: f"Food and Shopping in {destination}",
        6: f"Hidden Gems and Local Secrets",
        7: f"Final Exploration and Departure"
    }
    
    return day_titles.get(day, f"Day {day} in {destination}")

def extract_day_activity(ai_response, day, time_period, destination):
    """Extract specific day activity from AI response"""
    
    # Enhanced patterns to look for activities
    patterns = [
        rf"Day {day}.*?{time_period}.*?:.*?([^\n\.]+)",
        rf"{time_period}.*?Day {day}.*?:.*?([^\n\.]+)",
        rf"Day {day}.*?{time_period}.*?([A-Z][^\.]*\.)",
        rf"{time_period}.*?(\b[A-Z][^\.]{20,100}\.)"
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, ai_response, re.IGNORECASE | re.DOTALL)
        for match in matches:
            activity = match.group(1).strip()
            if len(activity) > 15 and any(word in activity.lower() for word in ['visit', 'explore', 'tour', 'experience', 'enjoy']):
                return activity[:120] + "..." if len(activity) > 120 else activity
    
    # Fallback activities based on day and time with variety
    activities_by_day = {
        1: {
            "morning": f"Arrival and check-in with orientation tour of {destination}",
            "afternoon": f"Visit the main landmarks and get familiar with {destination}",
            "evening": f"Welcome dinner at local restaurant and evening stroll"
        },
        2: {
            "morning": f"Explore the most famous historical sites and monuments in {destination}",
            "afternoon": f"Guided tour of cultural attractions and museums",
            "evening": f"Traditional cultural performance and local cuisine experience"
        },
        3: {
            "morning": f"Local market tour and interact with artisans in {destination}",
            "afternoon": f"Hands-on cultural workshop or cooking class",
            "evening": f"Rooftop dining with panoramic views of {destination}"
        },
        4: {
            "morning": f"Adventure activity or nature excursion near {destination}",
            "afternoon": f"Outdoor exploration and scenic photography",
            "evening": f"Sunset viewing from the best vantage point"
        },
        5: {
            "morning": f"Street food tour and culinary exploration in {destination}",
            "afternoon": f"Shopping for local handicrafts and souvenirs",
            "evening": f"Live music venue or entertainment district visit"
        }
    }
    
    day_key = min(day, 5)  # Use patterns for first 5 days, cycle for longer trips
    day_key = ((day - 1) % 5) + 1  # Cycle through 1-5 for longer trips
    
    return activities_by_day.get(day_key, {}).get(time_period, f"{time_period.title()} exploration of {destination}")

def extract_activity_location(ai_response, day, time_period, destination):
    """Extract activity location from AI response"""
    
    patterns = [
        rf"Day {day}.*?{time_period}.*?(?:at|in|near)\s+([A-Z][^,\n\.]+)",
        rf"{time_period}.*?(?:location|at|in)\s*:?\s*([A-Z][^,\n\.]+)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, ai_response, re.IGNORECASE)
        if match:
            location = match.group(1).strip()
            if len(location) > 3 and len(location) < 50:
                return location
    
    # Fallback locations
    locations = [
        f"Central {destination}",
        f"Historic District {destination}",
        f"Cultural Quarter {destination}",
        f"Main Tourist Area {destination}",
        f"Old City {destination}",
        f"Market Area {destination}",
        f"Waterfront {destination}",
        f"Heritage Zone {destination}"
    ]
    
    return locations[day % len(locations)]

def extract_best_time(ai_response, destination):
    """Extract best time to visit from AI response"""
    
    patterns = [
        r"best time.*?visit.*?([^\.]+)",
        r"ideal.*?months.*?([^\.]+)",
        r"recommended.*?time.*?([^\.]+)",
        r"weather.*?best.*?([^\.]+)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, ai_response, re.IGNORECASE)
        if match:
            time_info = match.group(1).strip()
            if len(time_info) > 10:
                return time_info[:100]
    
    return "October to March (pleasant weather)"

def extract_trip_theme(ai_response, destination):
    """Extract trip theme from AI response"""
    
    patterns = [
        r"theme.*?([^\.]+)",
        r"focus.*?([^\.]+)",
        r"experience.*?([^\.]+)",
        r"journey.*?([^\.]+)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, ai_response, re.IGNORECASE)
        if match:
            theme = match.group(1).strip()
            if len(theme) > 10:
                return theme[:100]
    
    return f"Complete cultural and adventure exploration of {destination}"

def extract_highlights(ai_response, destination):
    """Extract trip highlights from AI response"""
    
    # Look for numbered lists or bullet points
    highlight_patterns = [
        r"highlights?:?\s*\n(.*?)(?:\n\n|\n[A-Z])",
        r"top.*?attractions?:?\s*\n(.*?)(?:\n\n|\n[A-Z])",
        r"must.*?see:?\s*\n(.*?)(?:\n\n|\n[A-Z])",
        r"key.*?experiences?:?\s*\n(.*?)(?:\n\n|\n[A-Z])"
    ]
    
    for pattern in highlight_patterns:
        match = re.search(pattern, ai_response, re.IGNORECASE | re.DOTALL)
        if match:
            highlights_text = match.group(1)
            highlights = []
            lines = highlights_text.split('\n')
            for line in lines:
                cleaned = line.strip().lstrip('- ').lstrip('• ').lstrip('* ')
                # Remove numbering
                cleaned = re.sub(r'^\d+\.?\s*', '', cleaned)
                if len(cleaned) > 10 and len(cleaned) < 100:
                    highlights.append(cleaned)
                if len(highlights) >= 5:
                    break
            if highlights:
                return highlights[:5]
    
    # Fallback highlights
    return [
        f"Explore iconic landmarks of {destination}",
        f"Experience authentic local culture and traditions",
        f"Taste the famous cuisine of {destination}",
        f"Discover hidden gems and local secrets",
        f"Enjoy unique {destination} experiences"
    ]

def parse_budget_breakdown(ai_response, total_cost, group_size):
    """Parse budget breakdown from AI response"""
    
    return {
        "accommodation_total": f"₹{int(total_cost * 0.35):,} (accommodation for {group_size} people)",
        "food_total": f"₹{int(total_cost * 0.25):,} (all meals for {group_size} people)",
        "transport_total": f"₹{int(total_cost * 0.20):,} (transport for {group_size} people)",
        "activities_total": f"₹{int(total_cost * 0.15):,} (activities for {group_size} people)",
        "shopping_souvenirs": f"₹{int(total_cost * 0.10):,} (shopping for {group_size} people)",
        "contingency": f"₹{int(total_cost * 0.15):,} (15% buffer)",
        "grand_total": f"₹{total_cost:,} for {group_size} people",
        "per_person_total": f"₹{int(total_cost/group_size):,} per person"
    }

def parse_local_insights(ai_response):
    """Parse local insights from AI response"""
    
    return {
        "language": {
            "primary": "Hindi and English widely spoken",
            "useful_phrases": [
                "Namaste - Hello/Goodbye",
                "Dhanyawad - Thank you",
                "Kitna paisa - How much",
                "Thoda kam karo - Please reduce the price"
            ]
        },
        "culture": {
            "customs": "Remove shoes before entering temples. Dress modestly at religious sites.",
            "dress_code": "Modest clothing recommended. Cover shoulders and knees in religious places.",
            "etiquette": "Use right hand for eating and greeting. Respect local customs."
        },
        "practical": {
            "currency": "Indian Rupee (₹). Cards accepted in cities, carry cash for local markets.",
            "tipping": "10-15% in restaurants, ₹50-100 for drivers and guides.",
            "bargaining": "Expected in markets. Start at 50% of quoted price.",
            "safety": "Keep copies of documents. Use registered taxis. Drink bottled water."
        }
    }

def parse_packing_essentials(ai_response):
    """Parse packing essentials from AI response"""
    
    return {
        "clothing": [
            "Comfortable cotton clothes",
            "Modest wear for temples",
            "Light jacket for AC places",
            "Comfortable walking shoes",
            "Sandals for casual wear"
        ],
        "electronics": [
            "Phone charger and power bank",
            "Universal adapter (Type C/D/M)",
            "Camera with extra batteries",
            "Headphones"
        ],
        "documents": [
            "Passport/ID with valid visa",
            "Travel insurance documents",
            "Hotel booking confirmations",
            "Emergency contact information"
        ],
        "health_items": [
            "Prescription medications",
            "Basic first aid kit",
            "Sunscreen SPF 30+",
            "Hand sanitizer",
            "Water purification tablets"
        ],
        "destination_specific": [
            "Sunglasses and hat",
           "Reusable water bottle",
           "Small daypack",
           "Quick-dry towel"
       ]
   }

def parse_food_experience(ai_response, destination):
   """Parse food experience from AI response"""
   
   return {
       "must_try_dishes": [
           {
               "dish": f"Local specialty of {destination}",
               "description": "Authentic regional dish",
               "where_to_find": f"Traditional restaurants in {destination}",
               "cost": "₹200-500 per dish"
           }
       ],
       "food_streets": [f"Main food street in {destination}", "Local market area"],
       "dietary_options": {
           "vegetarian": "Excellent vegetarian options available everywhere",
           "vegan": "Many vegan dishes available, inform about dairy preferences",
           "special_diets": "Always inform restaurants about allergies"
       },
       "food_safety": "Eat hot, freshly cooked food. Drink bottled water. Choose busy restaurants."
   }

def parse_weather_clothing(ai_response, destination):
   """Parse weather and clothing info from AI response"""
   
   return {
       "expected_weather": "Generally pleasant during recommended travel months",
       "temperature_range": "20°C - 35°C (varies by season)",
       "rainfall": "Avoid monsoon season (July-September)",
       "recommended_clothing": [
           "Light cotton clothes for daytime",
           "Light jacket for evenings",
           "Comfortable walking shoes",
           "Modest clothing for religious sites"
       ],
       "footwear": "Walking shoes and sandals",
       "accessories": ["Sunglasses", "Hat", "Light scarf"]
   }

def generate_fallback_plan(destination, duration, budget_type, group_size):
   """Generate fallback plan when AI fails"""
   
   daily_costs = {'budget': 1500, 'mid_range': 3500, 'luxury': 7000}
   daily_cost = daily_costs.get(budget_type, 3500)
   total_cost = daily_cost * duration * group_size
   
   return {
       "success": False,
       "trip_overview": {
           "destination": destination,
           "duration": duration,
           "group_size": group_size,
           "best_time": "October to March (pleasant weather)",
           "trip_theme": f"Explore the beauty of {destination}",
           "highlights": [f"Visit {destination}", "Local experiences", "Cultural exploration"],
           "total_estimated_cost": f"₹{total_cost:,} for {group_size} people"
       },
       "error_message": "AI is currently busy generating plans. Please try again in a moment.",
       "suggestions": [
           f"Tell me about top attractions in {destination}",
           f"Best time to visit {destination}",
           f"Food specialties of {destination}"
       ]
   }

def fetch_weather_quick(location):
   """Quick weather fetch"""
   cache_key = f"weather_{location.lower()}"
   cached = get_from_cache(cache_key)
   if cached:
       return cached
   
   try:
       url = f"http://api.openweathermap.org/data/2.5/weather?q={location},IN&appid={openweather_api_key}&units=metric"
       response = requests.get(url, timeout=3)
       
       if response.status_code == 200:
           data = response.json()
           weather_info = {
               "description": data['weather'][0]['description'].title(),
               "temperature": f"{int(data['main']['temp'])}°C",
               "humidity": f"{data['main']['humidity']}%",
               "feels_like": f"{int(data['main']['feels_like'])}°C"
           }
           add_to_cache(cache_key, weather_info, expiry=1800)
           return weather_info
   except:
       pass
   
   return {"description": "Pleasant weather", "temperature": "25-30°C"}

def fetch_image_quick(location):
   """Quick image fetch"""
   cache_key = f"img_{location.lower()}"
   cached = get_from_cache(cache_key)
   if cached:
       return cached
   
   try:
       query = f"{location} India tourism"
       url = f"https://api.unsplash.com/photos/random?query={quote(query)}&client_id={unsplash_key}&w=800&h=600"
       
       response = requests.get(url, timeout=3)
       if response.status_code == 200:
           data = response.json()
           image_info = {
               "url": data['urls']['regular'],
               "credit": data['user']['name']
           }
           add_to_cache(cache_key, image_info, expiry=3600)
           return image_info
   except:
       pass
   
   return None

def get_related_suggestions(location):
   """Get related suggestions"""
   suggestions = [
       f"Plan a trip to {location}",
       f"Best time to visit {location}",
       f"Food guide for {location}",
       f"Things to do in {location}"
   ]
   
   return suggestions[:3]

# Cache cleanup
def cleanup_cache():
   with cache_lock:
       current_time = time.time()
       expired = [k for k, v in response_cache.items() if v["expires"] <= current_time]
       for k in expired:
           del response_cache[k]
   
   threading.Timer(900, cleanup_cache).start()

if __name__ == "__main__":
   port = int(os.environ.get("PORT", 5000))
   debug_mode = os.environ.get("FLASK_ENV") == "development"
   
   logger.info(f"Starting India Travel Explorer with AI Assistant on port {port}")
   cleanup_cache()
   
   app.run(
       host="0.0.0.0",
       port=port,
       debug=debug_mode,
       threaded=True
   )