from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
import os
from dotenv import load_dotenv
import secrets
from functools import wraps
import requests

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(16))

# Configure MongoDB
app.config["MONGO_URI"] = os.environ.get("MONGO_URI", "mongodb+srv://charankunda:saicharan12@logindatabasee.xjygbe3.mongodb.net/logindatabasee?retryWrites=true&w=majority&appName=logindatabasee")

# Initialize MongoDB
try:
    mongo = PyMongo(app)
    print("MongoDB connected successfully")
except Exception as e:
    print(f"MongoDB connection failed: {e}")

# Initialize OAuth
oauth = OAuth(app)

# Configure Google OAuth
google = oauth.register(
    name='google',
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Configure Facebook OAuth
facebook = oauth.register(
    name='facebook',
    client_id=os.environ.get("FACEBOOK_APP_ID"),
    client_secret=os.environ.get("FACEBOOK_APP_SECRET"),
    access_token_url='https://graph.facebook.com/oauth/access_token',
    authorize_url='https://www.facebook.com/dialog/oauth',
    api_base_url='https://graph.facebook.com/',
    client_kwargs={'scope': 'email'},
)

# Configure LinkedIn OAuth
linkedin = oauth.register(
    name='linkedin',
    client_id=os.environ.get("LINKEDIN_CLIENT_ID"),
    client_secret=os.environ.get("LINKEDIN_CLIENT_SECRET"),
    access_token_url='https://www.linkedin.com/oauth/v2/accessToken',
    authorize_url='https://www.linkedin.com/oauth/v2/authorization',
    api_base_url='https://api.linkedin.com/v2/',
    client_kwargs={'scope': 'r_liteprofile r_emailaddress'},
)

# Initialize database
def init_db():
    try:
        if 'users' not in mongo.db.list_collection_names():
            mongo.db.create_collection('users')
            print("Created users collection")
        mongo.db.users.create_index("username", unique=True, background=True)
        mongo.db.users.create_index("email", unique=True, background=True)
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Create or get user
def create_or_get_user(email, username, provider='local', provider_id=None):
    try:
        user = mongo.db.users.find_one({'email': email})
        if user:
            mongo.db.users.update_one({'_id': user['_id']}, {'$set': {'last_login_provider': provider}})
            return user
        else:
            new_user = {
                'username': username,
                'email': email,
                'password': None,
                'provider': provider,
                'provider_id': provider_id,
                'last_login_provider': provider
            }
            result = mongo.db.users.insert_one(new_user)
            new_user['_id'] = result.inserted_id
            return new_user
    except Exception as e:
        print(f"Error creating/getting user: {e}")
        return None

@app.route('/')
def index():
    init_db()
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('signin.html')

@app.route('/login', methods=['POST'])
def login():
    try:
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not username or not password:
            return render_template('signin.html', error="Please enter both username and password")
        user = mongo.db.users.find_one({'username': username})
        if user and user.get('password') and check_password_hash(user['password'], password):
            session['user'] = {
                'id': str(user['_id']),
                'username': user['username'],
                'email': user['email'],
                'provider': user.get('provider', 'local')
            }
            session.permanent = True
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            return render_template('signin.html', error="Invalid username or password")
    except Exception as e:
        print(f"Login error: {e}")
        return render_template('signin.html', error="An error occurred during login. Please try again.")

@app.route('/signup', methods=['POST'])
def signup():
    try:
        email = request.form.get('email', '').strip().lower()
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        if not email or not username or not password:
            return render_template('signin.html', error="Please fill in all fields")
        if len(password) < 6:
            return render_template('signin.html', error="Password must be at least 6 characters long")
        if len(username) < 3:
            return render_template('signin.html', error="Username must be at least 3 characters long")
        existing_user = mongo.db.users.find_one({'$or': [{'username': username}, {'email': email}]})
        if existing_user:
            if existing_user['username'] == username:
                return render_template('signin.html', error="Username already exists")
            else:
                return render_template('signin.html', error="Email already exists")
        hashed_password = generate_password_hash(password)
        result = mongo.db.users.insert_one({
            'username': username,
            'email': email,
            'password': hashed_password,
            'provider': 'local'
        })
        if result.inserted_id:
            return render_template('signin.html', success="Account created successfully! Please login.")
        else:
            return render_template('signin.html', error="Failed to create account. Please try again.")
    except Exception as e:
        print(f"Signup error: {e}")
        return render_template('signin.html', error="An error occurred during registration. Please try again.")

@app.route('/auth/<provider>')
def oauth_login(provider):
    try:
        redirect_uri = url_for('oauth_callback', provider=provider, _external=True)
        if provider == 'google':
            return google.authorize_redirect(redirect_uri)
        elif provider == 'facebook':
            return facebook.authorize_redirect(redirect_uri)
        elif provider == 'linkedin':
            return linkedin.authorize_redirect(redirect_uri)
        else:
            flash(f"OAuth provider '{provider}' is not supported", 'error')
            return redirect(url_for('index'))
    except Exception as e:
        print(f"OAuth login error for {provider}: {e}")
        flash(f"Error initiating {provider} login", 'error')
        return redirect(url_for('index'))

@app.route('/auth/<provider>/callback')
def oauth_callback(provider):
    try:
        user = None
        if provider == 'google':
            token = google.authorize_access_token()
            user_info = token.get('userinfo')
            if user_info:
                email = user_info.get('email')
                name = user_info.get('name', email.split('@')[0])
                provider_id = user_info.get('sub')
                user = create_or_get_user(email, name, 'google', provider_id)
        elif provider == 'facebook':
            token = facebook.authorize_access_token()
            resp = facebook.get('me?fields=id,name,email', token=token)
            user_info = resp.json()
            email = user_info.get('email')
            name = user_info.get('name', email.split('@')[0] if email else 'Facebook User')
            provider_id = user_info.get('id')
            if email:
                user = create_or_get_user(email, name, 'facebook', provider_id)
        elif provider == 'linkedin':
            token = linkedin.authorize_access_token()
            headers = {'Authorization': f'Bearer {token["access_token"]}'}
            profile_resp = requests.get('https://api.linkedin.com/v2/me', headers=headers)
            email_resp = requests.get(
                'https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))',
                headers=headers)
            if profile_resp.ok and email_resp.ok:
                profile_data = profile_resp.json()
                email_data = email_resp.json()
                email = email_data['elements'][0]['handle~']['emailAddress']
                name = f"{profile_data.get('localizedFirstName', '')} {profile_data.get('localizedLastName', '')}".strip()
                provider_id = profile_data.get('id')
                user = create_or_get_user(email, name or 'LinkedIn User', 'linkedin', provider_id)
        if user:
            session['user'] = {
                'id': str(user['_id']),
                'username': user['username'],
                'email': user['email'],
                'provider': provider
            }
            session.permanent = True
            flash(f'Welcome, {user["username"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(f'{provider.title()} login failed', 'error')
            return redirect(url_for('index'))
    except Exception as e:
        print(f"OAuth callback error for {provider}: {e}")
        flash(f'Error during {provider} login: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = session.get('user')
    return render_template('index.html', user=user)

@app.route('/logout')
def logout():
    username = session.get('user', {}).get('username', 'User')
    session.clear()
    flash(f'Goodbye, {username}! You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('signin.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('signin.html', error="Internal server error. Please try again later."), 500

@app.route('/health')
def health_check():
    try:
        mongo.db.users.find_one()
        return jsonify({"status": "healthy", "database": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

# Session config
app.permanent_session_lifetime = 3600  # seconds (1 hour)

if __name__ == '__main__':
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600
    app.run(debug=True, host='0.0.0.0', port=5001)
