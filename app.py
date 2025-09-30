"""
India Travel Explorer with Enhanced RAG-Powered AI Assistant, Monument Recognition, and Multi-Modal Input
Enhanced with comprehensive RAG integration and support for text, image, and voice inputs
"""

import os
import logging
import math
import time
import json
import threading
import re
import requests
import base64
import io
from urllib.parse import quote
from datetime import datetime, timedelta, timezone
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
import google.generativeai as genai
from PIL import Image
import speech_recognition as sr
from pydub import AudioSegment
import tempfile

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

# Access environment variables
google_api_key = os.getenv("GOOGLE_API_KEY")
unsplash_key = os.getenv("UNSPLASH_ACCESS_KEY")
openweather_api_key = os.getenv("OPENWEATHER_API_KEY")
spotify_api_key = os.getenv("SPOTIFY_API_KEY")
secret_key = os.getenv("SECRET_KEY", "india-travel-app-secret")
mongodb_uri = os.getenv("MONGODB_URI")
serper_api_key = os.getenv("SERPER_API_KEY")
news_api_key = os.getenv("NEWS_API_KEY")
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY")
PROJECT_NAME = os.getenv("ROBOFLOW_PROJECT_NAME")
WORKSPACE = os.getenv("ROBOFLOW_WORKSPACE")
VERSION = os.getenv("ROBOFLOW_VERSION")

# Upload folder for files
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'wav', 'mp3', 'ogg', 'm4a', 'flac'}

# Initialize Flask app
app = Flask(__name__)
app.secret_key = secret_key
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024  # 25MB for audio files
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

# Gemini AI Client Initialization
gemini_model = None
gemini_vision_model = None

MODEL_NAME = "gemini-2.0-flash"
VISION_MODEL_NAME = "gemini-2.0-flash"

try:
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set.")
    genai.configure(api_key=google_api_key)
    gemini_model = genai.GenerativeModel(MODEL_NAME)
    gemini_vision_model = genai.GenerativeModel(VISION_MODEL_NAME)
    logger.info(f"Gemini clients configured successfully")
except Exception as e:
    logger.critical(f"Failed to configure Gemini client: {e}")

# Initialize speech recognition
recognizer = sr.Recognizer()

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
stateCoordinates = {
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
    'Karnataka': [15.3173, 75.7139],
    'Tamil Nadu': [11.1271, 78.6569],
    'Kerala': [10.8505, 76.2711],
    'Andhra Pradesh': [15.9129, 79.7400],
    'Telangana': [18.1124, 79.0193],
    'Puducherry': [11.9416, 79.8083],
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

# Multi-Modal Input Processing Functions
def allowed_file(filename, file_type="image"):
    """Check if file extension is allowed"""
    if '.' not in filename:
        return False
    
    extension = filename.rsplit('.', 1)[1].lower()
    
    if file_type == "image":
        return extension in {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    elif file_type == "audio":
        return extension in {'wav', 'mp3', 'ogg', 'm4a', 'flac', 'webm'}
    else:
        return extension in ALLOWED_EXTENSIONS

def process_audio_to_text(audio_file_path):
    """Convert audio file to text using speech recognition"""
    try:
        # Convert audio to WAV format if needed
        audio = AudioSegment.from_file(audio_file_path)
        wav_path = audio_file_path.rsplit('.', 1)[0] + '.wav'
        audio.export(wav_path, format="wav")
        
        # Perform speech recognition
        with sr.AudioFile(wav_path) as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = recognizer.record(source)
        
        # Try Google Speech Recognition first, fallback to others
        try:
            text = recognizer.recognize_google(audio_data)
            logger.info(f"Audio transcribed successfully: {text[:50]}...")
            return text
        except sr.UnknownValueError:
            return "Could not understand the audio. Please speak clearly and try again."
        except sr.RequestError as e:
            logger.error(f"Speech recognition service error: {e}")
            return "Speech recognition service is currently unavailable."
    
    except Exception as e:
        logger.error(f"Audio processing error: {str(e)}")
        return "Error processing audio file. Please try again."
    
    finally:
        # Clean up temporary files
        try:
            if 'wav_path' in locals() and os.path.exists(wav_path):
                os.remove(wav_path)
        except:
            pass

def process_image_with_vision(image_path, user_query=""):
    """Process image using Gemini Vision model"""
    try:
        # Load and process image
        image = Image.open(image_path)
        
        # Create vision prompt
        vision_prompt = f"""
        You are an expert India travel assistant with vision capabilities.
        
        User Query: "{user_query}" (if provided)
        
        Analyze this image and provide helpful travel information:
        
        1. IDENTIFY: What do you see in this image? (monument, place, food, etc.)
        2. LOCATION: If it's a recognizable Indian location/monument, identify it
        3. TRAVEL INFO: Provide relevant travel information about this place/item
        4. RECOMMENDATIONS: Suggest related attractions, activities, or travel tips
        
        If this appears to be an Indian monument or tourist destination, provide:
        - Exact name and location
        - Historical significance
        - Best time to visit
        - Entry fees and timings
        - Nearby attractions
        - Travel tips
        
        Keep response under 300 words, be specific and helpful.
        """
        
        response = gemini_vision_model.generate_content([vision_prompt, image])
        
        # DON'T DELETE THE FILE HERE - let it be cleaned up later
        # os.remove(filepath)  <-- REMOVE THIS LINE
        
        return response.text.strip()
        
    except Exception as e:
        logger.error(f"Vision processing error: {str(e)}")
        return "Sorry, I couldn't analyze the image. Please try uploading a clear image of an Indian travel destination."
# Enhanced RAG Functions
def fetch_enhanced_rag_context(destination, query_type="general", interests=None, duration=None):
    """Enhanced RAG context fetcher with multiple sources and fallbacks"""
    
    rag_contexts = {}
    
    try:
        queries = build_contextual_queries(destination, query_type, interests, duration)
        
        for source, query in queries.items():
            try:
                if source == "serper_current":
                    rag_contexts[source] = fetch_serper_results(query, num_results=8)
                elif source == "news_recent":
                    rag_contexts[source] = fetch_news_results(query, num_results=5)
                elif source == "serper_detailed":
                    rag_contexts[source] = fetch_serper_results(query, num_results=6)
                    
            except Exception as e:
                logger.warning(f"Failed to fetch {source} for {destination}: {e}")
                rag_contexts[source] = ""
        
        combined_context = combine_rag_contexts(rag_contexts, destination)
        
        return {
            "combined_context": combined_context,
            "individual_contexts": rag_contexts,
            "context_quality": assess_combined_rag_quality(combined_context),
            "sources_used": list(rag_contexts.keys())
        }
        
    except Exception as e:
        logger.error(f"Enhanced RAG fetch failed for {destination}: {e}")
        return {
            "combined_context": f"Popular travel destination in India with cultural attractions.",
            "individual_contexts": {},
            "context_quality": "fallback",
            "sources_used": []
        }

def build_contextual_queries(destination, query_type, interests=None, duration=None):
    """Build contextual queries based on user inputs"""
    
    current_year = datetime.now().year
    current_month = datetime.now().strftime("%B")
    
    queries = {}
    
    if query_type == "general":
        queries["serper_current"] = f"{destination} India travel guide {current_year} attractions things to do"
        queries["news_recent"] = f"{destination} tourism news {current_year} travel updates"
        
    elif query_type == "trip_planning":
        base_query = f"{destination} India {duration} days itinerary {current_year}"
        
        if interests and len(interests) > 0:
            interests_str = " ".join(interests[:3])
            queries["serper_detailed"] = f"{base_query} {interests_str} budget travel"
        else:
            queries["serper_detailed"] = f"{base_query} complete travel guide"
            
        queries["serper_current"] = f"{destination} best places visit {current_month} {current_year}"
        queries["news_recent"] = f"{destination} travel tourism {current_year} latest updates"
        
    elif query_type == "specific":
        queries["serper_current"] = f"{destination} India detailed information {current_year}"
        
    return queries

def combine_rag_contexts(contexts, destination):
    """Intelligently combine RAG contexts from multiple sources"""
    
    combined = []
    priority_order = ["serper_detailed", "serper_current", "news_recent"]
    
    for source in priority_order:
        if source in contexts and contexts[source]:
            context_text = contexts[source].strip()
            if len(context_text) > 50:
                combined.append(f"=== {source.upper()} INFORMATION ===")
                combined.append(context_text)
                combined.append("")
    
    if not combined:
        combined.append(f"Limited real-time information available for {destination}. Using general travel knowledge.")
    
    return "\n".join(combined)

def assess_combined_rag_quality(combined_context):
    """Assess quality of combined RAG context"""
    
    if not combined_context or len(combined_context.strip()) < 100:
        return "poor"
    
    travel_keywords = [
        "attraction", "visit", "temple", "palace", "fort", "museum", "beach", "mountain",
        "food", "cuisine", "restaurant", "hotel", "accommodation", "cost", "price",
        "best time", "weather", "transport", "airport", "train", "bus", "taxi"
    ]
    
    keyword_count = sum(1 for keyword in travel_keywords 
                       if keyword in combined_context.lower())
    
    if keyword_count >= 8:
        return "excellent"
    elif keyword_count >= 5:
        return "good"
    elif keyword_count >= 3:
        return "fair"
    else:
        return "basic"

def fetch_serper_results(query, num_results=5):
    """Enhanced Serper API integration"""
    try:
        if not serper_api_key:
            return "SERPER_API_KEY missing."
        
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": serper_api_key, "Content-Type": "application/json"}
        payload = {"q": query, "num": num_results, "gl": "in", "hl": "en"}
        
        resp = requests.post(url, headers=headers, json=payload, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        
        items = []
        for r in data.get("organic", [])[:num_results]:
            snippet = r.get('snippet', '')
            if len(snippet) > 30:
                items.append(f"{r.get('title','')}\n{snippet}\nSource: {r.get('link','')}")
        
        return "\n\n".join(items) or "No search results found."
        
    except Exception as e:
        logger.error(f"Serper API error: {str(e)}")
        return f"Error fetching search results: {str(e)}"

def fetch_news_results(query, num_results=5):
    """Enhanced News API integration"""
    try:
        if not news_api_key:
            return "NEWS_API_KEY missing."
            
        url = f"https://newsapi.org/v2/everything?q={quote(query)}&pageSize={num_results}&language=en&apiKey={news_api_key}&sortBy=publishedAt"
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        data = resp.json()
        
        items = []
        for a in data.get("articles", [])[:num_results]:
            description = a.get('description', '')
            if description and len(description) > 30:
                items.append(f"{a.get('title','')}\n{description}\nSource: {a.get('url','')}")
        
        return "\n\n".join(items) or "No news articles found."
        
    except Exception as e:
        logger.error(f"News API error: {str(e)}")
        return f"Error fetching news results: {str(e)}"

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
    
    common_destinations = [
        'Mumbai', 'Delhi', 'Bangalore', 'Kolkata', 'Chennai', 'Hyderabad', 'Jaipur', 
        'Agra', 'Varanasi', 'Udaipur', 'Jodhpur', 'Pushkar', 'Rishikesh', 'Haridwar', 
        'Amritsar', 'Mysore', 'Cochin', 'Madurai', 'Shimla', 'Manali', 'Darjeeling', 
        'Ooty', 'Munnar', 'Coorg', 'Nainital', 'Mussoorie', 'Mount Abu', 'Kodaikanal', 
        'Lansdowne', 'Palolem', 'Arambol', 'Varkala', 'Kovalam', 'Gokarna', 'Leh Ladakh', 
        'Spiti Valley', 'Kasol', 'Hampi', 'Pondicherry', 'Andaman Islands', 'Rajasthan', 
        'Kerala', 'Goa', 'Himachal Pradesh', 'Tamil Nadu', 'Kashmir', 'Taj Mahal'
    ]
    
    for dest in common_destinations:
        if dest.lower() in text_lower:
            return dest
    
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
            
            client.admin.command('ping')
            return True
            
        except:
            logger.warning("Lost connection to MongoDB, attempting to reconnect...")
            return DatabaseConnection.connect()

# Initialize database connection
DatabaseConnection.connect()

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

@app.route('/monument-recognition')
def monument_recognition():
    """Serve the monument recognition HTML page"""
    return render_template('monument_recognition.html')

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
        "version": "2.0.0",
        "features": ["text_input", "image_input", "voice_input", "rag_powered", "multi_modal"]
    })

# Database Routes
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
def get_states_by_region(region):
    """Fetch states by region (north or south)"""
    try:
        valid_regions = ['north', 'south']
        if region.lower() not in valid_regions:
            return jsonify({
                "error": "Invalid region",
                "message": f"Region must be one of: {', '.join(valid_regions)}"
            }), 400
        
        projection = {
            'name': 1, 'capital': 1, 'region': 1, 'description': 1, 'image': 1,
            'touristPlaces': 1, 'cuisine': 1, 'culture': 1, 'bestTimeToVisit': 1,
            'transportation': 1, 'highlights': 1, 'hotels': 1
        }
        
        states = list(states_collection.find(
            {"region": region.lower()},
            projection
        ).sort("name", 1))
        
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
        projection = {
            'name': 1, 'capital': 1, 'region': 1, 'description': 1, 'image': 1,
            'touristPlaces': 1, 'cuisine': 1, 'culture': 1, 'bestTimeToVisit': 1,
            'transportation': 1, 'highlights': 1, 'hotels': 1
        }
        
        states = list(states_collection.find({}, projection).sort([
            ("region", 1), ("name", 1)
        ]))
        
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
        state_name = state_name.strip()
        
        if not state_name:
            return jsonify({
                "error": "Invalid state name",
                "message": "State name cannot be empty"
            }), 400
        
        state = states_collection.find_one({
            "name": {"$regex": f"^{state_name}$", "$options": "i"}
        })
        
        if not state:
            return jsonify({
                "error": "State not found",
                "message": f"No state found with name: {state_name}"
            }), 404
        
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
        if not place and state_name:
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
                    "description": detailed_place_info.get('description', f"A popular tourist destination in {state_name}.") if detailed_place_info else f"A popular tourist destination in {state_name}.",
                    "location": detailed_place_info.get('location', {"lat": coords[0], "lng": coords[1]}) if detailed_place_info else {"lat": coords[0], "lng": coords[1]},
                    "bestTimeToVisit": detailed_place_info.get('bestTimeToVisit', state.get("bestTimeToVisit", "Year-round")) if detailed_place_info else state.get("bestTimeToVisit", "Year-round"),
                    "entryFee": detailed_place_info.get('entryFee') if detailed_place_info else None,
                    "timings": detailed_place_info.get('timings') if detailed_place_info else None,
                    "images": detailed_place_info.get('images', []) if detailed_place_info else [],
                    "hotels": detailed_place_info.get('hotels', []) if detailed_place_info else [],
                    "restaurants": detailed_place_info.get('restaurants', []) if detailed_place_info else [],
                    "useGeoapify": True
                }
            else:
                return jsonify({
                    "error": "Tourist place not found",
                    "message": f"No details found for {place_name} in {state_name}"
                }), 404
        elif place:
            # If found in the dedicated tourist_places collection
            if not place.get('hotels') or not place.get('restaurants') or len(place.get('hotels', [])) == 0 or len(place.get('restaurants', [])) == 0:
                place['useGeoapify'] = True
                
                if 'hotels' not in place or place['hotels'] is None:
                    place['hotels'] = []
                if 'restaurants' not in place or place['restaurants'] is None:
                    place['restaurants'] = []
        else:
            return jsonify({
                "error": "Tourist place not found",
                "message": f"No details found for {place_name}"
            }), 404
        
        # Sanitize and return response
        sanitized_place = sanitize_json_response(place)
        return jsonify(sanitized_place)
        
    except Exception as e:
        logger.error(f"Error fetching tourist place details for '{place_name}': {str(e)}")
        return jsonify({
            "error": "Failed to fetch tourist place details",
            "message": "An error occurred while retrieving tourist place information."
        }), 500

# Monument Recognition Routes
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

# Multi-Modal Input Routes
@app.route('/api/multi-modal-message', methods=['POST'])
def handle_multi_modal_message():
    """Handle multi-modal input (text, image, voice)"""
    try:
        user_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        if not rate_limit_check(user_ip):
            return jsonify({"error": "Too many requests. Please wait 5 minutes.", "retry_after": 300}), 429

        # Initialize variables
        user_text = ""
        image_analysis = ""
        context = {}
        input_types = []

        # Handle text input
        if request.form.get('message'):
            user_text = request.form.get('message').strip()
            input_types.append("text")
            logger.info(f"Text input received: {user_text[:50]}...")

        # Handle context data
        if request.form.get('context'):
            try:
                context = json.loads(request.form.get('context'))
            except:
                context = {}

        # Handle image input
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file.filename and allowed_file(image_file.filename, "image"):
                try:
                    filename = secure_filename(image_file.filename)
                    timestamp = str(int(time.time()))
                    filename = f"{timestamp}_{filename}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    image_file.save(filepath)
                    
                    image_analysis = process_image_with_vision(filepath, user_text)
                    input_types.append("image")
                    logger.info(f"Image processed successfully: {filename}")
                    
                    # DELAY FILE CLEANUP - keep file for potential follow-up questions
                    # Schedule cleanup after 10 minutes instead of immediate deletion
                    def cleanup_file():
                        try:
                            if os.path.exists(filepath):
                                os.remove(filepath)
                                logger.info(f"Cleaned up file: {filename}")
                        except:
                            pass
                    
                    # Schedule cleanup in 10 minutes
                    import threading
                    cleanup_timer = threading.Timer(600.0, cleanup_file)  # 10 minutes
                    cleanup_timer.start()
                    
                except Exception as e:
                    logger.error(f"Image processing error: {str(e)}")
                    return jsonify({"error": "Failed to process image"}), 500

        # Handle audio input
        if 'audio' in request.files:
            audio_file = request.files['audio']
            if audio_file.filename and allowed_file(audio_file.filename, "audio"):
                try:
                    filename = secure_filename(audio_file.filename)
                    timestamp = str(int(time.time()))
                    filename = f"{timestamp}_{filename}"
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    audio_file.save(filepath)
                    
                    transcribed_text = process_audio_to_text(filepath)
                    if transcribed_text and not transcribed_text.startswith("Could not") and not transcribed_text.startswith("Error"):
                        user_text = transcribed_text if not user_text else f"{user_text} {transcribed_text}"
                        input_types.append("voice")
                        logger.info(f"Audio transcribed: {transcribed_text[:50]}...")
                    else:
                        return jsonify({"error": transcribed_text}), 400
                    
                    # Clean up uploaded file
                    os.remove(filepath)
                    
                except Exception as e:
                    logger.error(f"Audio processing error: {str(e)}")
                    return jsonify({"error": "Failed to process audio"}), 500

        # Validate we have some input
        if not user_text and not image_analysis:
            return jsonify({"error": "Please provide text, image, or voice input"}), 400

        # Combine inputs for processing
        combined_input = ""
        if image_analysis:
            combined_input += f"[IMAGE ANALYSIS]: {image_analysis}\n\n"
        if user_text:
            combined_input += f"[USER QUERY]: {user_text}"

        # Process with enhanced RAG
        response_data = process_enhanced_travel_query(combined_input, context, input_types)
        response_data["input_types"] = input_types

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Multi-modal processing error: {str(e)}")
        return jsonify({
            "error": "Sorry, I encountered an issue processing your request.",
            "suggestion": "Please try again with a clear text message, image, or voice input."
        }), 500

def process_enhanced_travel_query(user_input, context=None, input_types=None):
    """Enhanced RAG-powered travel query processor with multi-modal support"""
    if context is None:
        context = {}
    if input_types is None:
        input_types = ["text"]

    location = context.get("state") or context.get("place") or extract_smart_location(user_input)
    
    # Enhanced RAG with multiple sources
    rag_data = fetch_enhanced_rag_context(
        destination=location,
        query_type="specific",
        interests=context.get("interests", [])
    )
    
    rag_context = rag_data["combined_context"]
    context_quality = rag_data["context_quality"]
    
    # Multi-modal aware prompt
    input_type_str = ", ".join(input_types)
    travel_prompt = f"""
    You are India Travel Assistant - an expert on Indian destinations with multi-modal capabilities.
    You can understand text, images, and voice inputs to provide comprehensive travel assistance.

    Input Types Used: {input_type_str}
    User Input: "{user_input}"
    Location: {location}
    Context Quality: {context_quality}
    
    REAL-TIME KNOWLEDGE (Primary source):
    {rag_context}
    
    Instructions:
    1. Use the real-time knowledge extensively for accurate information
    2. If processing image input, acknowledge what you saw and provide specific details
    3. If processing voice input, confirm understanding and respond conversationally
    4. Include specific details from context (places, costs, timing)
    5. Be enthusiastic but factual
    
    Format response (under 300 words) with these sections:
    🏛️ OVERVIEW (2-3 sentences about {location})
    📅 BEST TIME (specific months with reasons)
    🎯 TOP ATTRACTIONS (3-4 must-visit places)
    🍽️ FOOD HIGHLIGHTS (2-3 local specialties)
    🌟 INSIDER TIP (unique insight from real-time data)
    
    Ground every claim in the provided real-time knowledge.
    """

    try:
        if not gemini_model:
            raise Exception("Gemini client not initialized.")

        response = gemini_model.generate_content(
            travel_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=1000,
                top_p=0.9,
                top_k=40
            ),
            request_options={"timeout": 30}
        )
        
        text_reply = response.text.strip() if response.text else None
        
        if not text_reply or len(text_reply) < 80:
            raise Exception("Generated response insufficient")
            
    except Exception as e:
        logger.error(f"Enhanced Gemini error for {location}: {str(e)}")
        text_reply = generate_enhanced_fallback_response(location, user_input, rag_context, context_quality)

    return {
        "response": text_reply,
        "location": location,
        "weather": fetch_weather_quick(location),
        "image_url": fetch_image_quick(location),
        "timestamp": int(time.time()),
        "suggestions": generate_smart_suggestions(location, user_input),
        "rag_source": "enhanced_multi_source",
        "rag_quality": context_quality,
        "confidence_score": calculate_enhanced_confidence(text_reply, rag_context),
        "sources_used": rag_data["sources_used"],
        "multi_modal": True
    }

def generate_enhanced_fallback_response(location, user_input, rag_context, quality):
    """Generate enhanced fallback response"""
    
    attractions = extract_attractions_from_context(rag_context)
    food_info = extract_food_from_context(rag_context)
    
    response = f"""
🏛️ OVERVIEW
{location} is a captivating destination in India. {"Current information shows various attractions and experiences" if quality != "poor" else "Limited current data available, but"} {location} offers rich cultural heritage.

📅 BEST TIME  
{"Based on available information, " if attractions else ""}October to March generally offers pleasant weather for exploring {location}.

🎯 ATTRACTIONS  
{", ".join(attractions[:3]) if attractions else f"Historical sites, cultural landmarks, and local markets in {location}"} are worth visiting.

🍽️ FOOD  
{food_info if food_info else f"Traditional regional cuisine and local specialties"} await food enthusiasts in {location}.

🌟 INSIDER TIP  
{"Current data suggests" if quality == "good" else "For the most current information,"} check local recommendations and consider using our detailed trip planner for comprehensive {location} insights.
"""
    
    return response.strip()

def extract_attractions_from_context(context):
    """Extract attractions from RAG context"""
    attractions = []
    
    patterns = [
        r'\b([A-Z][a-z]+\s+(?:Fort|Palace|Temple|Museum|Beach|Hill|Lake|Park|Garden|Market))\b',
        r'\b([A-Z][a-z]+\s+[A-Z][a-z]+\s+(?:Temple|Fort|Palace|Museum))\b',
        r'visit\s+([A-Z][^,\.]+?)(?:\s*,|\s*\.|\s+for)',
        r'famous\s+([A-Z][^,\.]+?)(?:\s*,|\s*\.|\s+is)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, context)
        for match in matches:
            if len(match) > 5 and len(match) < 40:
                attractions.append(match.strip())
            if len(attractions) >= 5:
                break
    
    return list(dict.fromkeys(attractions))

def extract_food_from_context(context):
    """Extract food information from RAG context"""
    food_keywords = ['cuisine', 'food', 'dish', 'specialty', 'delicacy', 'restaurant', 'street food']
    
    for keyword in food_keywords:
        pattern = rf'{keyword}[^\.]*?([A-Z][^\.]+?)\.?(?:\s|$)'
        match = re.search(pattern, context, re.IGNORECASE)
        if match:
            food_text = match.group(1).strip()
            if len(food_text) > 10 and len(food_text) < 60:
                return food_text
    
    return None

def calculate_enhanced_confidence(response, rag_context):
    """Enhanced confidence calculation"""
    confidence = 0.4
    
    if not response or not rag_context:
        return confidence
    
    rag_words = set(word.lower() for word in rag_context.split() if len(word) > 4)
    response_words = set(word.lower() for word in response.split() if len(word) > 4)
    
    overlap = len(rag_words.intersection(response_words))
    if overlap > 15:
        confidence += 0.4
    elif overlap > 8:
        confidence += 0.25
    elif overlap > 4:
        confidence += 0.1
    
    required_sections = ['overview', 'best time', 'attractions', 'food', 'tip']
    sections_found = sum(1 for section in required_sections 
                        if section.replace(' ', '').lower() in response.lower().replace(' ', ''))
    confidence += (sections_found / len(required_sections)) * 0.2
    
    return min(confidence, 1.0)

@app.route("/api/message", methods=["POST"])
def handle_message():
    """Traditional text-only chat message handler"""
    try:
        user_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        if not rate_limit_check(user_ip):
            return jsonify({"error": "Too many requests. Please wait 5 minutes.", "retry_after": 300}), 429

        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 415

        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400

        user_input = data.get("message", "").strip()
        context = data.get("context", {})
        use_news = data.get("news", False)

        if not user_input or len(user_input) > 500:
            return jsonify({"error": "Please enter a valid message (max 500 characters)"}), 400

        cache_key = f"msg_{hash(user_input.lower())}_{hash(str(context))}_{use_news}"
        cached_response = get_from_cache(cache_key)
        if cached_response:
            return jsonify(cached_response)

        response_data = process_enhanced_travel_query(user_input, context, ["text"])
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
    """Enhanced AI Trip Planner with comprehensive RAG integration"""
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

        # Extract and validate all trip parameters
        destination = data.get("destination", "").strip()
        duration = int(data.get("duration", 3))
        budget_type = data.get("budget_type", "mid_range")
        interests = data.get("interests", [])
        travel_style = data.get("travel_style", "balanced")
        group_size = int(data.get("group_size", 2))
        use_news = data.get("use_news", False)
        
        # Validation
        if not destination:
            return jsonify({"error": "Please specify a destination"}), 400
        if duration < 1 or duration > 30:
            return jsonify({"error": "Duration must be between 1-30 days"}), 400
        if group_size < 1 or group_size > 20:
            return jsonify({"error": "Group size must be between 1-20 people"}), 400
        
        logger.info(f"Enhanced trip planning: {destination}, {duration}d, {budget_type}, {group_size} people, interests: {interests}")
        
        # Check cache first
        cache_key = f"enhanced_trip_{destination.lower()}_{duration}_{budget_type}_{travel_style}_{group_size}_{hash(str(interests))}"
        cached_plan = get_from_cache(cache_key)
        if cached_plan:
            logger.info("Returning cached enhanced trip plan")
            return jsonify(cached_plan)
        
        # Generate enhanced AI-powered trip plan
        trip_plan = generate_enhanced_ai_trip_plan(
            destination=destination,
            duration=duration,
            budget_type=budget_type,
            interests=interests,
            travel_style=travel_style,
            group_size=group_size,
            use_news=use_news
        )
        
        # Cache the plan for 3 hours
        add_to_cache(cache_key, trip_plan, expiry=10800)
        
        logger.info("Enhanced AI trip plan generated successfully")
        return jsonify(trip_plan)

    except Exception as e:
        logger.error(f"Error planning trip: {str(e)}")
        return jsonify({
            "error": "Couldn't create your trip plan. Please try again.",
            "suggestion": "Try with a destination like 'Rajasthan' or 'Kerala'"
        }), 500

def generate_enhanced_ai_trip_plan(destination, duration, budget_type, interests, travel_style, group_size, use_news=False):
    """Fully AI and RAG-powered trip planner without hardcoded content"""
    
    logger.info(f"Generating fully dynamic trip plan: {destination}, {duration}d, {budget_type}")
    
    # Enhanced RAG context for comprehensive trip planning
    rag_data = fetch_comprehensive_rag_context(
        destination=destination,
        duration=duration,
        budget_type=budget_type,
        interests=interests,
        travel_style=travel_style,
        group_size=group_size
    )
    
    rag_context = rag_data["combined_context"]
    context_quality = rag_data["context_quality"]
    
    # Build comprehensive interest string
    interests_str = ", ".join(interests) if interests else "general cultural exploration"
    
    # Fully dynamic AI prompt that relies entirely on RAG data
    trip_prompt = f"""
    You are an expert Indian travel consultant with access to the most current travel information. Create a comprehensive {duration}-day itinerary for {destination}, India using ONLY the real-time information provided below.

    TRIP PARAMETERS:
    - Destination: {destination}
    - Duration: {duration} days  
    - Budget Level: {budget_type}
    - Group Size: {group_size} people
    - Travel Style: {travel_style}
    - Key Interests: {interests_str}
    
    CURRENT REAL-TIME TRAVEL DATA:
    {rag_context}
    
    INSTRUCTIONS:
    1. Base ALL recommendations on the real-time data provided above
    2. Extract specific place names, costs, timings from the data
    3. Calculate realistic budgets based on current Indian prices mentioned in the data
    4. Create detailed daily schedules using actual attractions and activities from the information
    5. If specific costs aren't mentioned, estimate based on similar places in the data
    
    REQUIRED OUTPUT STRUCTURE:

    TRIP OVERVIEW:
    - Best time to visit (extract from data)
    - Trip theme based on selected interests
    - 5 key highlights (specific places from the data)
    - Total estimated cost for {group_size} people
    
    DAILY ITINERARY:
    For each day (Day 1 to Day {duration}), provide:
    
    Day X: [Specific title based on real places]
    Morning (9 AM - 12 PM):
    - Activity: [Specific attraction/activity from data]
    - Location: [Exact location from data]
    - Cost per person: [Extract or estimate from data]
    - Duration: [Realistic timing]
    - Tips: [Based on information in data]
    
    Afternoon (2 PM - 6 PM):
    - Activity: [Different specific attraction from data]
    - Location: [Exact location from data]  
    - Cost per person: [Extract or estimate from data]
    - Duration: [Realistic timing]
    - Tips: [Based on information in data]
    
    Evening (7 PM - 10 PM):
    - Activity: [Dining/entertainment from data]
    - Location: [Specific restaurant/area from data]
    - Cost per person: [Extract or estimate from data]
    - Duration: [Realistic timing]
    - Tips: [Based on information in data]
    
    Accommodation:
    - Hotel name/type: [Extract from data or realistic recommendation]
    - Location: [Based on data]
    - Cost per night for {group_size} people: [Based on budget level and data]
    - Amenities: [Based on budget level]
    
    Daily total per person: [Sum of all activities + accommodation share]
    
    BUDGET BREAKDOWN:
    Extract and calculate from the real-time data:
    - Accommodation total: [Based on {duration} nights]
    - Food total: [Based on meal costs from data]
    - Transport total: [Based on transport costs from data]
    - Activities total: [Based on entry fees from data]
    - Shopping/Miscellaneous: [Estimate from data]
    - Grand total for {group_size} people
    - Per person cost
    
    PRACTICAL INFORMATION:
    Extract from the real-time data:
    - Best local transport options
    - Cultural tips and customs
    - Must-try food items and where to find them
    - Current weather information
    - Packing suggestions based on activities and weather
    - Local language tips
    - Safety and health recommendations
    - Current travel restrictions or important updates
    
    IMPORTANT: Use ONLY information from the provided real-time data. If specific information isn't available, clearly state that and provide the best estimate based on similar information in the data. Make the itinerary feel authentic and current by incorporating real places, costs, and practical details from the research data.
    """

    try:
        response = gemini_model.generate_content(
            trip_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=6000,
                top_p=0.9,
                top_k=40
            ),
            request_options={"timeout": 120}
        )
        
        ai_response = response.text.strip()
        
        if not ai_response or len(ai_response) < 500:
            raise Exception("AI response insufficient for comprehensive trip plan")

        # Parse the AI-generated response dynamically
        structured_plan = parse_dynamic_ai_response(
            destination=destination,
            duration=duration, 
            budget_type=budget_type,
            group_size=group_size,
            ai_response=ai_response,
            rag_context=rag_context,
            context_quality=context_quality
        )

        # Enrich with current data
        structured_plan.update({
            "success": True,
            "destination": destination,
            "rag_quality": context_quality,
            "raw_ai_response": ai_response,
            "weather": fetch_weather_quick(destination),
            "destination_image": fetch_image_quick(destination),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sources_used": rag_data["sources_used"],
            "planning_confidence": calculate_dynamic_confidence(ai_response, rag_context, interests)
        })

        logger.info(f"Dynamic trip plan generated successfully for {destination}")
        return structured_plan

    except Exception as e:
        logger.error(f"Dynamic trip planning error: {str(e)}")
        return generate_dynamic_fallback_plan(destination, duration, budget_type, group_size, interests, rag_context)

def fetch_comprehensive_rag_context(destination, duration, budget_type, interests, travel_style, group_size):
    """Fetch comprehensive RAG context for fully dynamic planning"""
    
    rag_contexts = {}
    current_year = datetime.now().year
    current_month = datetime.now().strftime("%B")
    
    # Build multiple specific queries for comprehensive data
    queries = {
        "attractions": f"{destination} India top attractions places to visit {current_year} entry fees timings",
        "accommodation": f"{destination} India hotels {budget_type} accommodation {current_year} prices booking",
        "food": f"{destination} India restaurants local food specialties {current_year} prices where to eat",
        "transport": f"{destination} India local transport taxi bus metro {current_year} costs how to travel",
        "activities": f"{destination} India {' '.join(interests)} activities things to do {current_year}",
        "budget": f"{destination} India travel budget {budget_type} costs {duration} days {current_year}",
        "practical": f"{destination} India travel tips cultural customs weather {current_month} {current_year}",
        "current_news": f"{destination} tourism news travel updates {current_year}"
    }
    
    # Fetch from multiple sources
    for category, query in queries.items():
        try:
            # Get both search and news results for comprehensive coverage
            serper_results = fetch_serper_results(query, num_results=8)
            news_results = fetch_news_results(query, num_results=3)
            
            combined_results = f"SEARCH RESULTS:\n{serper_results}\n\nNEWS UPDATES:\n{news_results}"
            rag_contexts[category] = combined_results
            
        except Exception as e:
            logger.warning(f"Failed to fetch {category} data for {destination}: {e}")
            rag_contexts[category] = ""
    
    # Combine all contexts intelligently
    combined_context = build_comprehensive_context(rag_contexts, destination)
    
    return {
        "combined_context": combined_context,
        "individual_contexts": rag_contexts,
        "context_quality": assess_comprehensive_rag_quality(combined_context),
        "sources_used": list(rag_contexts.keys())
    }

def build_comprehensive_context(contexts, destination):
    """Build comprehensive context from all RAG sources"""
    
    combined = []
    
    # Priority order for context sections
    priority_sections = [
        ("attractions", "=== ATTRACTIONS AND PLACES TO VISIT ==="),
        ("accommodation", "=== ACCOMMODATION OPTIONS ==="),
        ("food", "=== FOOD AND DINING ==="),
        ("transport", "=== TRANSPORTATION ==="),
        ("activities", "=== ACTIVITIES AND EXPERIENCES ==="),
        ("budget", "=== BUDGET AND COSTS ==="),
        ("practical", "=== PRACTICAL TRAVEL INFORMATION ==="),
        ("current_news", "=== CURRENT TRAVEL UPDATES ===")
    ]
    
    for section_key, header in priority_sections:
        if section_key in contexts and contexts[section_key].strip():
            context_text = contexts[section_key].strip()
            if len(context_text) > 100:  # Only include substantial content
                combined.append(header)
                combined.append(context_text)
                combined.append("")  # Spacing
    
    if not combined:
        combined = [f"Limited real-time information available for {destination}. Using general travel knowledge and best practices."]
    
    return "\n".join(combined)

def assess_comprehensive_rag_quality(combined_context):
    """Assess quality of comprehensive RAG context"""
    
    if not combined_context or len(combined_context.strip()) < 500:
        return "poor"
    
    # Check for comprehensive travel information
    quality_indicators = [
        # Attractions
        "entry fee", "timings", "hours", "visit", "attraction", "temple", "fort", "palace", "museum",
        # Accommodation  
        "hotel", "accommodation", "booking", "room", "stay", "resort", "guesthouse",
        # Food
        "restaurant", "food", "cuisine", "dish", "specialty", "eat", "dining", "meal",
        # Transport
        "transport", "taxi", "bus", "train", "metro", "rickshaw", "uber", "ola",
        # Budget
        "cost", "price", "budget", "rupees", "₹", "expensive", "cheap", "affordable",
        # Practical
        "weather", "temperature", "season", "culture", "custom", "language", "tip"
    ]
    
    indicator_count = sum(1 for indicator in quality_indicators 
                         if indicator in combined_context.lower())
    
    if indicator_count >= 15:
        return "excellent"
    elif indicator_count >= 10:
        return "good" 
    elif indicator_count >= 6:
        return "fair"
    else:
        return "basic"

def parse_dynamic_ai_response(destination, duration, budget_type, group_size, ai_response, rag_context, context_quality):
    """Parse AI response completely dynamically without hardcoded values"""
    
    # Extract trip overview dynamically
    trip_overview = extract_trip_overview_dynamic(ai_response, destination, duration, group_size)
    
    # Extract daily itinerary dynamically  
    daily_itinerary = extract_daily_itinerary_dynamic(ai_response, duration, destination)
    
    # Extract budget breakdown dynamically
    budget_breakdown = extract_budget_breakdown_dynamic(ai_response, group_size)
    
    # Extract practical information dynamically
    local_insights = extract_local_insights_dynamic(ai_response)
    food_experience = extract_food_experience_dynamic(ai_response) 
    packing_essentials = extract_packing_essentials_dynamic(ai_response)
    weather_clothing = extract_weather_clothing_dynamic(ai_response)
    
    return {
        "success": True,
        "trip_overview": trip_overview,
        "daily_itinerary": daily_itinerary,
        "budget_breakdown": budget_breakdown,
        "local_insights": local_insights,
        "packing_essentials": packing_essentials,
        "food_experience": food_experience,
        "weather_and_clothing": weather_clothing,
        "full_ai_response": ai_response,
        "rag_integration_quality": context_quality
    }

def extract_trip_overview_dynamic(ai_response, destination, duration, group_size):
    """Extract trip overview completely from AI response"""
    
    # Extract best time to visit
    best_time_patterns = [
        r"best time.*?visit.*?:?\s*([^\n\.]+)",
        r"ideal.*?time.*?:?\s*([^\n\.]+)",
        r"recommended.*?months?.*?:?\s*([^\n\.]+)"
    ]
    
    best_time = "October to March"  # Default fallback
    for pattern in best_time_patterns:
        match = re.search(pattern, ai_response, re.IGNORECASE)
        if match:
            best_time = match.group(1).strip()
            break
    
    # Extract trip theme
    theme_patterns = [
        r"trip theme.*?:?\s*([^\n\.]+)",
        r"theme.*?:?\s*([^\n\.]+)",
        r"focus.*?:?\s*([^\n\.]+)"
    ]
    
    trip_theme = f"Cultural exploration of {destination}"  # Default
    for pattern in theme_patterns:
        match = re.search(pattern, ai_response, re.IGNORECASE)
        if match:
            trip_theme = match.group(1).strip()
            break
    
    # Extract highlights
    highlights = extract_highlights_list_dynamic(ai_response)
    
    # Extract total cost
    total_cost = extract_total_cost_dynamic(ai_response, group_size)
    
    return {
        "destination": destination,
        "duration": duration,
        "group_size": group_size,
        "best_time": best_time,
        "trip_theme": trip_theme,
        "highlights": highlights,
        "total_estimated_cost": total_cost["total"],
        "per_person_cost": total_cost["per_person"]
    }

def extract_highlights_list_dynamic(ai_response):
    """Extract highlights list from AI response"""
    
    # Look for highlights section
    highlights_patterns = [
        r"(?:highlights|key highlights|must see|top experiences).*?:?\s*((?:[-•*]\s*[^\n]+\n?)+)",
        r"(?:highlights|key highlights|must see|top experiences).*?:?\s*((?:\d+\.\s*[^\n]+\n?)+)"
    ]
    
    for pattern in highlights_patterns:
        match = re.search(pattern, ai_response, re.IGNORECASE | re.DOTALL)
        if match:
            highlights_text = match.group(1)
            highlights = []
            
            # Parse bullet points or numbered lists
            lines = highlights_text.split('\n')
            for line in lines:
                # Remove bullets, numbers, and clean up
                cleaned = re.sub(r'^[-•*\d.)\s]+', '', line.strip())
                if len(cleaned) > 10 and len(cleaned) < 200:
                    highlights.append(cleaned)
                if len(highlights) >= 6:
                    break
            
            if highlights:
                return highlights
    
    # Fallback: look for any lists in the response
    list_pattern = r"(?:^[-•*]\s*(.+)$)"
    matches = re.findall(list_pattern, ai_response, re.MULTILINE)
    
    if matches:
        return [match.strip() for match in matches if len(match.strip()) > 10][:5]
    
    # Final fallback
    return [f"Explore {destination}", "Local cultural experiences", "Traditional cuisine", "Historical sites", "Scenic attractions"]

def extract_daily_itinerary_dynamic(ai_response, duration, destination):
    """Extract daily itinerary completely from AI response"""
    
    daily_activities = []
    
    for day in range(1, duration + 1):
        day_data = extract_single_day_dynamic(ai_response, day, destination)
        daily_activities.append(day_data)
    
    return daily_activities

def extract_single_day_dynamic(ai_response, day_num, destination):
    """Extract single day information from AI response"""
    
    # Extract day title
    day_title_patterns = [
        rf"Day {day_num}[:\s]*([^\n]+)",
        rf"Day {day_num}[:\-\s]+([^\n]+)"
    ]
    
    day_title = f"Day {day_num} in {destination}"
    for pattern in day_title_patterns:
        match = re.search(pattern, ai_response, re.IGNORECASE)
        if match:
            day_title = match.group(1).strip()
            break
    
    # Extract morning activity
    morning = extract_time_period_activity(ai_response, day_num, "morning")
    
    # Extract afternoon activity  
    afternoon = extract_time_period_activity(ai_response, day_num, "afternoon")
    
    # Extract evening activity
    evening = extract_time_period_activity(ai_response, day_num, "evening")
    
    # Extract accommodation info
    accommodation = extract_accommodation_info(ai_response, day_num)
    
    # Calculate daily total
    daily_total = calculate_daily_total_from_activities(morning, afternoon, evening)
    
    return {
        "day": day_num,
        "title": day_title,
        "overview": f"Day {day_num} exploration",
        "morning": morning,
        "afternoon": afternoon, 
        "evening": evening,
        "accommodation": accommodation,
        "daily_total_per_person": daily_total
    }

def extract_time_period_activity(ai_response, day_num, time_period):
    """Extract activity for specific time period"""
    
    # Patterns to find time period activities
    patterns = [
        rf"Day {day_num}.*?{time_period}.*?:?\s*\n\s*[-•*]?\s*Activity[:\s]*([^\n]+)",
        rf"Day {day_num}.*?{time_period}.*?:?\s*\n\s*[-•*]?\s*([^\n]+)",
        rf"{time_period}.*?Day {day_num}.*?:?\s*([^\n]+)",
        rf"{time_period}.*?\(.*?\):?\s*\n\s*[-•*]?\s*([^\n]+)"
    ]
    
    activity = f"{time_period.title()} exploration"
    location = f"Central area"
    cost = "₹300-500"
    tips = f"Enjoy the {time_period} experience"
    
    # Try to extract specific information
    for pattern in patterns:
        match = re.search(pattern, ai_response, re.IGNORECASE | re.DOTALL)
        if match:
            activity_text = match.group(1).strip()
            if len(activity_text) > 10:
                activity = activity_text[:200]
                break
    
    # Extract location if mentioned
    location_patterns = [
        rf"{time_period}.*?Location[:\s]*([^\n]+)",
        rf"{time_period}.*?at\s+([A-Z][^,\n\.]+)"
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, ai_response, re.IGNORECASE)
        if match:
            location = match.group(1).strip()
            break
    
    # Extract cost if mentioned
    cost_patterns = [
        rf"{time_period}.*?Cost[:\s]*([₹\d,\-\s]+per person)",
        rf"{time_period}.*?₹([₹\d,\-\s]+per person)"
    ]
    
    for pattern in cost_patterns:
        match = re.search(pattern, ai_response, re.IGNORECASE)
        if match:
            cost = f"₹{match.group(1).strip()}"
            break
    
    return {
        "time": get_time_period_hours(time_period),
        "activity": activity,
        "location": location,
        "duration": get_duration_for_period(time_period),
        "cost_per_person": cost,
        "tips": tips
    }

def get_time_period_hours(time_period):
    """Get time range for period"""
    times = {
        "morning": "09:00 AM - 12:00 PM",
        "afternoon": "02:00 PM - 06:00 PM", 
        "evening": "07:00 PM - 10:00 PM"
    }
    return times.get(time_period.lower(), "Full day")

def get_duration_for_period(time_period):
    """Get duration for time period"""
    durations = {
        "morning": "3 hours",
        "afternoon": "4 hours",
        "evening": "3 hours"
    }
    return durations.get(time_period.lower(), "3-4 hours")

def extract_accommodation_info(ai_response, day_num):
    """Extract accommodation information"""
    
    # Patterns for accommodation
    patterns = [
        rf"Day {day_num}.*?Accommodation.*?:?\s*\n\s*[-•*]?\s*([^\n]+)",
        rf"Accommodation.*?Day {day_num}.*?:?\s*([^\n]+)"
    ]
    
    hotel_name = "Recommended accommodation"
    cost = "₹2000-3000"
    
    for pattern in patterns:
        match = re.search(pattern, ai_response, re.IGNORECASE | re.DOTALL)
        if match:
            hotel_info = match.group(1).strip()
            if len(hotel_info) > 10:
                hotel_name = hotel_info
                break
    
    # Extract cost if mentioned
    cost_match = re.search(r"₹([\d,\-\s]+).*?night", ai_response, re.IGNORECASE)
    if cost_match:
        cost = f"₹{cost_match.group(1).strip()} per night"
    
    return {
        "name": hotel_name,
        "type": "Hotel",
        "location": "Central area",
        "cost_per_night": cost,
        "amenities": ["WiFi", "AC", "Restaurant"],
        "booking_tip": "Book in advance for better rates"
    }

def calculate_daily_total_from_activities(morning, afternoon, evening):
    """Calculate daily total from activity costs"""
    
    def extract_cost_number(cost_str):
        numbers = re.findall(r'(\d+)', cost_str)
        if numbers:
            return int(numbers[0])
        return 300  # Default
    
    morning_cost = extract_cost_number(morning["cost_per_person"])
    afternoon_cost = extract_cost_number(afternoon["cost_per_person"]) 
    evening_cost = extract_cost_number(evening["cost_per_person"])
    
    total = morning_cost + afternoon_cost + evening_cost
    return f"₹{total}"

def extract_budget_breakdown_dynamic(ai_response, group_size):
    """Extract budget breakdown from AI response"""
    
    # Look for budget section
    budget_section = re.search(r"budget breakdown.*?:?\s*(.*?)(?=\n\n|\n[A-Z]|$)", ai_response, re.IGNORECASE | re.DOTALL)
    
    budget_data = {
        "accommodation_total": "₹15,000",
        "food_total": "₹12,000", 
        "transport_total": "₹8,000",
        "activities_total": "₹6,000",
        "grand_total": "₹41,000",
        "per_person_total": f"₹{41000 // group_size:,}"
    }
    
    if budget_section:
        budget_text = budget_section.group(1)
        
        # Extract specific costs
        cost_patterns = {
            "accommodation_total": r"accommodation.*?₹([\d,]+)",
            "food_total": r"food.*?₹([\d,]+)",
            "transport_total": r"transport.*?₹([\d,]+)",
            "activities_total": r"activities.*?₹([\d,]+)",
            "grand_total": r"(?:total|grand total).*?₹([\d,]+)"
        }
        
        for key, pattern in cost_patterns.items():
            match = re.search(pattern, budget_text, re.IGNORECASE)
            if match:
                amount = match.group(1).replace(',', '')
                budget_data[key] = f"₹{int(amount):,}"
        
        # Calculate per person if grand total found
        if "grand_total" in budget_data:
            total_amount = int(re.sub(r'[₹,]', '', budget_data["grand_total"]))
            budget_data["per_person_total"] = f"₹{total_amount // group_size:,}"
    
    return budget_data

def extract_total_cost_dynamic(ai_response, group_size):
    """Extract total cost from AI response"""
    
    # Look for total cost mentions
    cost_patterns = [
        r"total.*?cost.*?₹([\d,]+)",
        r"grand total.*?₹([\d,]+)",
        r"estimated.*?cost.*?₹([\d,]+)"
    ]
    
    total_cost = 35000  # Default fallback
    
    for pattern in cost_patterns:
        match = re.search(pattern, ai_response, re.IGNORECASE)
        if match:
            total_cost = int(match.group(1).replace(',', ''))
            break
    
    return {
        "total": f"₹{total_cost:,} for {group_size} people",
        "per_person": f"₹{total_cost // group_size:,} per person"
    }

def extract_local_insights_dynamic(ai_response):
    """Extract local insights from AI response"""
    
    insights = {
        "language": {"primary": "Hindi and English", "useful_phrases": []},
        "culture": {"customs": "", "dress_code": "", "etiquette": ""},
        "practical": {"currency": "Indian Rupee (₹)", "tipping": "", "safety": ""}
    }
    
    # Extract language info
    language_match = re.search(r"language.*?:?\s*([^\n\.]+)", ai_response, re.IGNORECASE)
    if language_match:
        insights["language"]["primary"] = language_match.group(1).strip()
    
    # Extract cultural customs
    customs_match = re.search(r"(?:customs|culture).*?:?\s*([^\n\.]+)", ai_response, re.IGNORECASE)
    if customs_match:
        insights["culture"]["customs"] = customs_match.group(1).strip()
    
    # Extract practical info
    practical_patterns = [
        (r"tipping.*?:?\s*([^\n\.]+)", "tipping"),
        (r"safety.*?:?\s*([^\n\.]+)", "safety")
    ]
    
    for pattern, key in practical_patterns:
        match = re.search(pattern, ai_response, re.IGNORECASE)
        if match:
            insights["practical"][key] = match.group(1).strip()
    
    return insights

def extract_food_experience_dynamic(ai_response):
    """Extract food experience from AI response"""
    
    food_info = {
        "must_try_dishes": [],
        "food_streets": [],
        "dietary_options": {"vegetarian": "Available", "vegan": "Limited options"},
        "food_safety": "Eat at busy places, drink bottled water"
    }
    
    # Extract must-try dishes
    dishes_patterns = [
        r"must try.*?:?\s*(.*?)(?=\n\n|\n[A-Z])",
        r"local.*?food.*?:?\s*(.*?)(?=\n\n|\n[A-Z])",
        r"specialties.*?:?\s*(.*?)(?=\n\n|\n[A-Z])"
    ]
    
    for pattern in dishes_patterns:
        match = re.search(pattern, ai_response, re.IGNORECASE | re.DOTALL)
        if match:
            dishes_text = match.group(1).strip()
            # Extract dish names
            dishes = re.findall(r'[-•*]?\s*([^,\n]+)', dishes_text)
            food_info["must_try_dishes"] = [dish.strip() for dish in dishes if len(dish.strip()) > 3][:5]
            break
    
    return food_info

def extract_packing_essentials_dynamic(ai_response):
    """Extract packing essentials from AI response"""
    
    packing = {
        "clothing": [],
        "electronics": [],
        "documents": [],
        "health_items": [],
        "destination_specific": []
    }
    
    # Look for packing section
    packing_match = re.search(r"packing.*?:?\s*(.*?)(?=\n\n|\n[A-Z]|$)", ai_response, re.IGNORECASE | re.DOTALL)
    
    if packing_match:
        packing_text = packing_match.group(1)
        
        # Extract items
        items = re.findall(r'[-•*]?\s*([^,\n]+)', packing_text)
        
        # Categorize items (basic categorization)
        clothing_keywords = ['cloth', 'shirt', 'pant', 'shoe', 'jacket', 'dress']
        electronics_keywords = ['charg', 'camera', 'phone', 'power', 'adapter']
        
        for item in items:
            item = item.strip()
            if len(item) > 3:
                if any(keyword in item.lower() for keyword in clothing_keywords):
                    packing["clothing"].append(item)
                elif any(keyword in item.lower() for keyword in electronics_keywords):
                    packing["electronics"].append(item)
                else:
                    packing["destination_specific"].append(item)
    
    # Add defaults if empty
    if not packing["clothing"]:
        packing["clothing"] = ["Comfortable clothing", "Walking shoes"]
    if not packing["electronics"]:
        packing["electronics"] = ["Phone charger", "Camera"]
    
    return packing

def extract_weather_clothing_dynamic(ai_response):
    """Extract weather and clothing info from AI response"""
    
    weather_info = {
        "expected_weather": "Pleasant",
        "temperature_range": "20°C - 30°C", 
        "recommended_clothing": [],
        "accessories": []
    }
    
    # Extract weather information
    weather_patterns = [
        r"weather.*?:?\s*([^\n\.]+)",
        r"temperature.*?:?\s*([^\n\.]+)",
        r"climate.*?:?\s*([^\n\.]+)"
    ]
    
    for pattern in weather_patterns:
        match = re.search(pattern, ai_response, re.IGNORECASE)
        if match:
            weather_info["expected_weather"] = match.group(1).strip()
            break
    
    # Extract clothing recommendations
    clothing_patterns = [
        r"clothing.*?:?\s*(.*?)(?=\n\n|\n[A-Z])",
        r"wear.*?:?\s*(.*?)(?=\n\n|\n[A-Z])"
    ]
    
    for pattern in clothing_patterns:
        match = re.search(pattern, ai_response, re.IGNORECASE | re.DOTALL)
        if match:
            clothing_text = match.group(1).strip()
            items = re.findall(r'[-•*]?\s*([^,\n]+)', clothing_text)
            weather_info["recommended_clothing"] = [item.strip() for item in items if len(item.strip()) > 3][:5]
            break
    
    return weather_info

def calculate_dynamic_confidence(ai_response, rag_context, interests):
    """Calculate confidence based on AI response quality and RAG integration"""
    
    confidence = 0.3  # Base confidence
    
    # Check response length and detail
    if len(ai_response) > 2000:
        confidence += 0.2
    elif len(ai_response) > 1000:
        confidence += 0.1
    
    # Check RAG context quality
    if len(rag_context) > 2000:
        confidence += 0.2
    elif len(rag_context) > 1000:
        confidence += 0.1
    
    # Check for specific travel elements
    travel_elements = [
        "cost", "price", "₹", "hotel", "restaurant", "attraction", "transport",
        "morning", "afternoon", "evening", "day 1", "day 2", "accommodation",
        "food", "weather", "packing", "culture", "language", "tips"
    ]
    
    element_count = sum(1 for element in travel_elements if element in ai_response.lower())
    confidence += min(element_count / len(travel_elements), 0.3)
    
    # Check interest integration
    if interests:
        interest_integration = sum(1 for interest in interests if interest.lower() in ai_response.lower())
        confidence += min(interest_integration / len(interests) * 0.1, 0.1)
    
    return min(confidence, 1.0)

def generate_dynamic_fallback_plan(destination, duration, budget_type, group_size, interests, rag_context=""):
    """Generate completely dynamic fallback plan using available RAG data"""
    
    logger.info(f"Generating dynamic fallback plan for {destination}")
    
    # Use RAG context for fallback if available
    if rag_context and len(rag_context) > 200:
        fallback_prompt = f"""
        Using the available information below, create a basic {duration}-day travel plan for {destination}:
        
        Available Information:
        {rag_context[:1000]}
        
        Create a simple structure with:
        1. Trip overview with estimated cost for {group_size} people
        2. {duration} days of basic activities
        3. Simple budget breakdown
        
        Keep it realistic and practical.
        """
        
        try:
            response = gemini_model.generate_content(
                fallback_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.5,
                    max_output_tokens=1500
                )
            )
            
            if response.text and len(response.text) > 300:
                return parse_dynamic_ai_response(
                    destination, duration, budget_type, group_size,
                    response.text, rag_context, "basic"
                )
        except Exception as e:
            logger.error(f"Fallback generation failed: {e}")
    
    # Final fallback with minimal structure
    base_cost_per_day = {"budget": 1500, "mid_range": 3000, "luxury": 5500}
    daily_cost = base_cost_per_day.get(budget_type, 3000)
    total_cost = daily_cost * duration * group_size
    
    return {
        "success": False,
        "trip_overview": {
            "destination": destination,
            "duration": duration,
            "group_size": group_size,
            "best_time": "October to March",
            "trip_theme": f"Exploration of {destination}",
            "highlights": [
                f"Discover {destination}",
                "Experience local culture",
                "Taste regional cuisine",
                "Visit historical sites",
                "Enjoy local attractions"
            ],
            "total_estimated_cost": f"₹{total_cost:,} for {group_size} people",
            "per_person_cost": f"₹{total_cost // group_size:,} per person"
        },
        "daily_itinerary": generate_minimal_itinerary(destination, duration, budget_type, group_size),
        "budget_breakdown": {
            "accommodation_total": f"₹{int(total_cost * 0.4):,}",
            "food_total": f"₹{int(total_cost * 0.3):,}",
            "transport_total": f"₹{int(total_cost * 0.2):,}",
            "activities_total": f"₹{int(total_cost * 0.1):,}",
            "grand_total": f"₹{total_cost:,}",
            "per_person_total": f"₹{total_cost // group_size:,}"
        },
        "local_insights": generate_basic_insights(destination),
        "packing_essentials": generate_basic_packing(),
        "food_experience": generate_basic_food_guide(destination),
        "weather_and_clothing": generate_basic_weather_guide(),
        "message": "This is a basic plan. For detailed recommendations, try again or check current travel resources.",
        "full_ai_response": "Fallback plan generated due to limited data availability."
    }

def generate_minimal_itinerary(destination, duration, budget_type, group_size):
    """Generate minimal itinerary structure"""
    
    cost_levels = {
        "budget": {"morning": 200, "afternoon": 300, "evening": 400},
        "mid_range": {"morning": 400, "afternoon": 600, "evening": 800}, 
        "luxury": {"morning": 800, "afternoon": 1200, "evening": 1500}
    }
    
    costs = cost_levels.get(budget_type, cost_levels["mid_range"])
    daily_activities = []
    
    for day in range(1, duration + 1):
        day_plan = {
            "day": day,
            "title": f"Day {day} - Explore {destination}",
            "overview": f"Discover {destination} attractions and culture",
            "morning": {
                "time": "09:00 AM - 12:00 PM",
                "activity": f"Visit major attractions in {destination}",
                "location": f"Central {destination}",
                "duration": "3 hours",
                "cost_per_person": f"₹{costs['morning']}",
                "tips": "Start early to avoid crowds"
            },
            "afternoon": {
                "time": "02:00 PM - 06:00 PM",
                "activity": f"Explore local markets and cultural sites",
                "location": f"Historic area of {destination}",
                "duration": "4 hours", 
                "cost_per_person": f"₹{costs['afternoon']}",
                "tips": "Good time for sightseeing"
            },
            "evening": {
                "time": "07:00 PM - 10:00 PM",
                "activity": f"Local dining and evening entertainment",
                "location": f"Restaurant area in {destination}",
                "duration": "3 hours",
                "cost_per_person": f"₹{costs['evening']}",
                "tips": "Try local cuisine"
            },
            "accommodation": {
                "name": f"Hotel in {destination}",
                "type": "Hotel",
                "location": f"Central {destination}",
                "cost_per_night": f"₹{2000 + (day * 200)} for {group_size} people",
                "amenities": ["WiFi", "AC", "Restaurant"],
                "booking_tip": "Book in advance"
            },
            "daily_total_per_person": f"₹{costs['morning'] + costs['afternoon'] + costs['evening']}"
        }
        
        daily_activities.append(day_plan)
    
    return daily_activities

def generate_basic_insights(destination):
    """Generate basic local insights"""
    return {
        "language": {
            "primary": "Hindi and English commonly spoken",
            "useful_phrases": ["Namaste (Hello)", "Dhanyawad (Thank you)"]
        },
        "culture": {
            "customs": "Respect local customs and dress modestly at religious sites",
            "dress_code": "Conservative clothing recommended",
            "etiquette": "Remove shoes at temples"
        },
        "practical": {
            "currency": "Indian Rupee (₹)",
            "tipping": "10-15% at restaurants",
            "safety": "Keep valuables secure, drink bottled water"
        }
    }

def generate_basic_packing():
    """Generate basic packing list"""
    return {
        "clothing": ["Comfortable clothes", "Walking shoes", "Light jacket"],
        "electronics": ["Phone charger", "Camera", "Power bank"],
        "documents": ["ID/Passport", "Travel insurance", "Bookings"],
        "health_items": ["Sunscreen", "Basic medicines", "Hand sanitizer"],
        "destination_specific": ["Sunglasses", "Water bottle", "Daypack"]
    }

def generate_basic_food_guide(destination):
    """Generate basic food guide"""
    return {
        "must_try_dishes": [f"Local specialties of {destination}"],
        "food_streets": ["Local markets", "Restaurant areas"],
        "dietary_options": {
            "vegetarian": "Widely available",
            "vegan": "Limited but available"
        },
        "food_safety": "Eat at busy places, avoid tap water"
    }

def generate_basic_weather_guide():
    """Generate basic weather guide"""
    return {
        "expected_weather": "Variable by season",
        "temperature_range": "15°C - 35°C depending on season",
        "recommended_clothing": ["Light cotton clothes", "Comfortable shoes"],
        "accessories": ["Sunglasses", "Hat", "Light jacket"]
    }

# Updated process_enhanced_travel_query for better RAG integration
def process_enhanced_travel_query(user_input, context=None, input_types=None):
    """Enhanced RAG-powered travel query processor - fully dynamic"""
    if context is None:
        context = {}
    if input_types is None:
        input_types = ["text"]

    location = context.get("state") or context.get("place") or extract_smart_location(user_input)
    
    # Enhanced RAG with comprehensive data
    rag_data = fetch_comprehensive_rag_context(
        destination=location,
        duration=3,  # Default for chat queries
        budget_type="mid_range",
        interests=context.get("interests", []),
        travel_style="balanced",
        group_size=2
    )
    
    rag_context = rag_data["combined_context"]
    context_quality = rag_data["context_quality"]
    
    # Multi-modal aware prompt - fully RAG dependent
    input_type_str = ", ".join(input_types)
    travel_prompt = f"""
    You are an expert India Travel Assistant using only current, real-time information.
    
    Input Types: {input_type_str}
    User Query: "{user_input}"
    Location: {location}
    
    REAL-TIME TRAVEL DATA (Use ONLY this information):
    {rag_context}
    
    Instructions:
    1. Answer using ONLY the real-time data provided above
    2. If image input: acknowledge what you saw and provide specific details
    3. If voice input: confirm understanding conversationally
    4. Extract specific places, costs, timings from the data
    5. Be enthusiastic but ground everything in the provided data
    
    Format response (under 300 words):
    🏛️ OVERVIEW (2-3 sentences using data about {location})
    📅 BEST TIME (extract from data or estimate)
    🎯 TOP ATTRACTIONS (specific places from data)
    🍽️ FOOD HIGHLIGHTS (specific dishes/restaurants from data)
    🌟 INSIDER TIP (unique insight from the real-time data)
    
    Base your entire response on the provided real-time information.
    """

    try:
        if not gemini_model:
            raise Exception("Gemini client not initialized.")

        response = gemini_model.generate_content(
            travel_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.6,
                max_output_tokens=800,
                top_p=0.9
            ),
            request_options={"timeout": 30}
        )
        
        text_reply = response.text.strip() if response.text else None
        
        if not text_reply or len(text_reply) < 100:
            text_reply = generate_rag_fallback_response(location, rag_context, context_quality)
            
    except Exception as e:
        logger.error(f"Enhanced query processing error: {str(e)}")
        text_reply = generate_rag_fallback_response(location, rag_context, context_quality)

    return {
        "response": text_reply,
        "location": location,
        "weather": fetch_weather_quick(location),
        "image_url": fetch_image_quick(location),
        "timestamp": int(time.time()),
        "suggestions": generate_dynamic_suggestions(location, user_input, rag_context),
        "rag_source": "comprehensive_multi_source",
        "rag_quality": context_quality,
        "confidence_score": calculate_dynamic_confidence(text_reply, rag_context, []),
        "sources_used": rag_data["sources_used"],
        "multi_modal": True
    }

def generate_rag_fallback_response(location, rag_context, quality):
    """Generate fallback response using available RAG context"""
    
    if rag_context and len(rag_context) > 200:
        # Extract key information from RAG context
        attractions = extract_attractions_from_context(rag_context)[:3]
        food_mentions = extract_food_from_context(rag_context)
        
        response = f"""
🏛️ OVERVIEW
{location} offers diverse travel experiences. {"Current information indicates" if quality != "poor" else "Available data suggests"} various attractions and cultural sites worth exploring.

📅 BEST TIME  
October to March generally provides pleasant weather conditions for visiting {location}.

🎯 TOP ATTRACTIONS  
{", ".join(attractions) if attractions else f"Historical sites and cultural landmarks in {location}"} are highlighted in recent travel information.

🍽️ FOOD HIGHLIGHTS  
{food_mentions if food_mentions else f"Regional cuisine and local specialties"} represent the culinary culture of {location}.

🌟 INSIDER TIP  
{"Based on current travel data" if quality == "good" else "For updated information"}, check local recommendations and consider seasonal variations when planning your {location} visit.
"""
    else:
        response = f"""
🏛️ OVERVIEW
{location} is a notable destination in India with cultural and historical significance worth exploring.

📅 BEST TIME  
October to March typically offers the most comfortable weather for travel.

🎯 TOP ATTRACTIONS  
Historical monuments, cultural sites, and local markets are common highlights in {location}.

🍽️ FOOD HIGHLIGHTS  
Traditional regional cuisine and local street food provide authentic taste experiences.

🌟 INSIDER TIP  
For current information and detailed recommendations, consult recent travel guides or local tourism offices.
"""
    
    return response.strip()

def generate_dynamic_suggestions(location, user_input, rag_context):
    """Generate suggestions based on RAG context"""
    
    base_suggestions = [
        f"Plan a detailed trip to {location}",
        f"Best attractions in {location}",
        f"Food guide for {location}"
    ]
    
    # Extract additional suggestions from RAG context
    if rag_context:
        # Look for mentioned places in the context
        places = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:\s+(?:Fort|Palace|Temple|Museum|Beach|Market)))\b', rag_context)
        if places:
            base_suggestions.append(f"Tell me about {places[0]}")
    
    return base_suggestions[:4]

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

def generate_smart_suggestions(location, user_input=None):
    """Generate smart travel suggestions"""
    suggestions = [
        f"Plan a trip to {location}",
        f"Best time to visit {location}",
        f"Food guide for {location}",
        f"Things to do in {location}",
        f"Budget travel tips for {location}"
    ]
    
    return suggestions[:3]

# Cache cleanup
def cleanup_cache():
    """Clean up expired cache entries"""
    with cache_lock:
        current_time = time.time()
        expired = [k for k, v in response_cache.items() if v["expires"] <= current_time]
        for k in expired:
            del response_cache[k]
    
    threading.Timer(900, cleanup_cache).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    
    logger.info(f"Starting Enhanced India Travel Explorer with RAG-Powered AI Assistant on port {port}")
    logger.info("Features: Multi-modal input (text/image/voice), Enhanced RAG, Monument Recognition")
    
    cleanup_cache()
    
    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug_mode,
        threaded=True
    )
