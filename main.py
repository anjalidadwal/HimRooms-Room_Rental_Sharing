from flask import Flask, render_template, request, session, redirect, url_for, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from urllib.parse import quote
import random
import json
import os
import re
import secrets
import math
import datetime
import tempfile
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# 1. Initialize the Flask application
app = Flask(__name__)

# Use environment variable for secret key, fallback to generated key if not set
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))

# --- EMAIL CONFIGURATION ---
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 465))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'False').lower() == 'true'
app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', app.config['MAIL_USERNAME'])

mail = Mail(app)

# --- DATABASE CONFIGURATION ---
# Use a managed database URI when deployed on Vercel.
# For local development this falls back to SQLite.
is_vercel = os.getenv('VERCEL', '0') == '1'
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.getenv('SQLALCHEMY_DATABASE_URI')
    or os.getenv('DATABASE_URL')
    or ('sqlite:////tmp/himrooms.db' if is_vercel else 'sqlite:///himrooms.db')
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS', 'False').lower() == 'true'

# Use ephemeral temp storage for uploads on Vercel.
UPLOAD_FOLDER = os.getenv(
    'UPLOAD_FOLDER',
    os.path.join(tempfile.gettempdir(), 'flatmate_uploads') if is_vercel else os.path.join('static', 'uploads')
)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize the database
db = SQLAlchemy(app)

# --- DATABASE MODELS ---
class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True) # Automatically creates a unique ID (1, 2, 3...)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    date_sent = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class RentAgreement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_name = db.Column(db.String(100))
    owner_mobile = db.Column(db.String(15))
    owner_address = db.Column(db.Text)
    tenant_name = db.Column(db.String(100))
    tenant_mobile = db.Column(db.String(15))
    tenant_address = db.Column(db.Text)
    prop_city = db.Column(db.String(50))
    prop_address = db.Column(db.Text)
    prop_pincode = db.Column(db.String(10))
    rent_amount = db.Column(db.Integer)
    deposit = db.Column(db.Integer)
    validity = db.Column(db.Integer)
    start_date = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(15), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    avatar = db.Column(db.String(255), nullable=False, default='avatarm.jpg')
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        return {
            'name': self.name,
            'email': self.email,
            'mobile': self.mobile,
            'city': self.city,
            'avatar': self.avatar,
        }

# NEW: Model to store all property visit requests
class VisitRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    property_title = db.Column(db.String(200)) 
    name = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(15), nullable=False)
    visit_datetime = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# NEW: Model to store generated rent receipts
class RentReceipt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rent_amount = db.Column(db.Integer, nullable=False)
    prop_address = db.Column(db.Text, nullable=False)
    landlord_name = db.Column(db.String(100), nullable=False)
    landlord_pan = db.Column(db.String(20))
    start_date = db.Column(db.String(20), nullable=False)
    months = db.Column(db.Integer, nullable=False)
    tenant_name = db.Column(db.String(100), nullable=False)
    tenant_mobile = db.Column(db.String(15), nullable=False)
    tenant_email = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# NEW: Model to store Verification Requests
class VerificationRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    # We store the filenames of the uploaded images
    aadhaar_front_filename = db.Column(db.String(255))
    aadhaar_back_filename = db.Column(db.String(255))
    # We can store the services requested as a comma-separated string
    services_requested = db.Column(db.String(200)) 
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class ApplyInterest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), default='')
    mobile = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# Create the database file and tables if they don't exist yet
with app.app_context():
    db.create_all()

def load_property_data():
    # Use os.path to ensure Flask finds the file no matter where you run the script from
    file_path = os.path.join(app.root_path, 'data.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def resolve_property_city(location):
    location_text = (location or '')
    parts = [normalize_city_token(p) for p in location_text.split(',') if normalize_city_token(p)]

    city_name = ''
    if len(parts) >= 2 and parts[-1].lower() == 'india':
        city_name = parts[-2]
    elif parts:
        city_name = parts[0]

    city_name = city_name.title() if city_name else 'City'
    city_slug = re.sub(r'[^a-z0-9]+', '-', city_name.lower()).strip('-')
    return city_name, city_slug


def slugify(value):
    return re.sub(r'[^a-z0-9]+', '-', (value or '').strip().lower()).strip('-')


def normalize_city_token(token):
    cleaned = (token or '').strip()
    cleaned = re.sub(r'^in\s+', '', cleaned, flags=re.IGNORECASE)
    return cleaned


def location_city_tokens(location):
    return [
        normalize_city_token(part)
        for part in (location or '').split(',')
        if normalize_city_token(part) and normalize_city_token(part).lower() != 'india'
    ]


def location_city_slugs(location):
    return [slugify(token) for token in location_city_tokens(location)]


EXCLUDED_CITY_SLUGS = {
    'aleo',
    'amb',
    'bundla',
    'delhi',
    'dhalli',
    'dhalpur',
    'dharamkot',
    'gehrwin',
    'indira-market',
    'kangra-fort-area',
    'kasumti',
    'lohna',
    'nadaun',
    'nagrota-surian',
    'old-manali',
    'phase-1',
    'prini',
    'sadar-bazar',
    'salogra',
    'shahpur',
    'simsa',
    'totu',
    'vashisht',
    'yol-cantt',
}


def extract_supported_cities(properties):
    city_map = {}
    city_counts = {}
    for prop in properties:
        for part in location_city_tokens(prop.get('location', '')):
            city_slug = slugify(part)
            if city_slug in EXCLUDED_CITY_SLUGS:
                continue
            city_map[city_slug] = part.title()
            city_counts[city_slug] = city_counts.get(city_slug, 0) + 1

    popular_order = [
        'Shimla', 'Dharamshala', 'Manali', 'Kangra', 'Palampur', 'Chamba',
        'Bilaspur', 'Sundernagar', 'Nurpur', 'Hamirpur', 'Solan', 'Kullu',
        'Mandi', 'Baddi', 'Nahan', 'Paonta', 'Yol', 'Una', 'Nagrota Bagwan',
    ]

    ordered = []
    seen = set()
    for city_name in popular_order:
        city_slug = slugify(city_name)
        if city_slug in city_map and city_slug not in seen:
            ordered.append({'name': city_map[city_slug], 'slug': city_slug, 'count': city_counts.get(city_slug, 0)})
            seen.add(city_slug)

    for city_slug, city_name in sorted(city_map.items(), key=lambda x: x[1]):
        if city_slug not in seen:
            ordered.append({'name': city_name, 'slug': city_slug, 'count': city_counts.get(city_slug, 0)})

    return ordered


def resolve_city_slug(city_slug, properties):
    requested_slug = slugify(city_slug)
    cities = extract_supported_cities(properties)
    supported = {city['slug'] for city in cities}

    if requested_slug in supported:
        return requested_slug

    # Handles variants such as paonta <-> paonta-sahib.
    for known_slug in supported:
        if known_slug.startswith(requested_slug + '-') or requested_slug.startswith(known_slug + '-'):
            return known_slug

    return requested_slug


def get_city_name_by_slug(city_slug, properties):
    resolved_slug = resolve_city_slug(city_slug, properties)
    cities = extract_supported_cities(properties)
    for city in cities:
        if city['slug'] == resolved_slug:
            return city['name']
    return resolved_slug.replace('-', ' ').title()


def filter_properties_by_slug(properties, city_slug, category=None):
    resolved_slug = resolve_city_slug(city_slug, properties)
    filtered = [
        prop for prop in properties
        if resolved_slug in location_city_slugs(prop.get('location', ''))
    ]

    if category:
        filtered = [prop for prop in filtered if prop.get('category') == category]

    return filtered


def get_city_images():
    return {
        'shimla': 'images/Shimla.png',
        'dharamshala': 'images/Dharamshala.png',
        'manali': 'images/manali.png',
        'kangra': 'images/Kangra.png',
        'palampur': 'images/Palampur.png',
        'chamba': 'images/Chamba.png',
        'bilaspur': 'images/Bilaspur.png',
        'sundernagar': 'images/Sundernagar.png',
        'nurpur': 'images/Nurpur.png',
        'hamirpur': 'images/Hamirpur.png',
        'solan': 'images/solan.png',
        'kullu': 'images/Kullu.png',
        'mandi': 'images/Mandi.png',
        'baddi': 'images/baddi.png',
        'nahan': 'images/NAHAN.png',
        'paonta': 'images/paonta.png',
        'paonta-sahib': 'images/paonta.png',
        'yol': 'images/YOL.png',
        'una': 'images/UNA.png',
        'nagrota-bagwan': 'images/NAGROTA BAGWAN.png',
    }


def build_city_cards(properties):
    supported_cities = extract_supported_cities(properties)
    city_images = get_city_images()

    cards = []
    for city in supported_cities:
        cards.append({
            'name': city['name'],
            'slug': city['slug'],
            'image': city_images.get(city['slug'], 'images/Shimla.png'),
            'count': city.get('count', 0),
        })

    return cards


def filter_properties(properties, city_name, category=None):
    city_regex = re.compile(rf'\b{re.escape(city_name)}\b', re.IGNORECASE)
    filtered = [prop for prop in properties if city_regex.search(prop.get('location', ''))]

    if category:
        filtered = [prop for prop in filtered if prop.get('category') == category]

    return filtered

def get_user_by_email(email):
    normalized = normalize_email(email)
    if not normalized:
        return None
    return User.query.filter_by(email=normalized).first()


def save_user(user_data):
    email = normalize_email(user_data.get('email'))
    if not email:
        return None

    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email=email)

    user.name = user_data.get('name') or user.name
    user.mobile = user_data.get('mobile') or user.mobile
    user.city = user_data.get('city') or user.city
    user.avatar = user_data.get('avatar') or getattr(user, 'avatar', 'avatarm.jpg')

    db.session.add(user)
    db.session.commit()
    return user


def load_premium_data():
    file_path = os.path.join(app.root_path, 'premium_data.json')
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except FileNotFoundError:
        return []


def enrich_premium_properties(properties):
    enriched = []
    for index, prop in enumerate(properties, start=1):
        entry = dict(prop)
        entry['premium_id'] = index
        entry['city_slug'] = slugify(entry.get('city', ''))
        enriched.append(entry)
    return enriched


def extract_premium_cities(properties):
    city_map = {}
    city_counts = {}

    for prop in properties:
        city_name = (prop.get('city') or '').strip()
        if not city_name:
            continue
        city_slug = slugify(city_name)
        city_map[city_slug] = city_name.title()
        city_counts[city_slug] = city_counts.get(city_slug, 0) + 1

    preferred_order = ['shimla', 'dharamshala', 'kullu', 'manali']

    ordered = []
    seen = set()
    for city_slug in preferred_order:
        if city_slug in city_map and city_slug not in seen:
            ordered.append({
                'slug': city_slug,
                'name': city_map[city_slug],
                'count': city_counts.get(city_slug, 0),
            })
            seen.add(city_slug)

    for city_slug, city_name in sorted(city_map.items(), key=lambda item: item[1]):
        if city_slug in seen:
            continue
        ordered.append({
            'slug': city_slug,
            'name': city_name,
            'count': city_counts.get(city_slug, 0),
        })

    return ordered


def filter_premium_by_city_slug(properties, city_slug):
    target_slug = slugify(city_slug)
    if not target_slug:
        return properties
    return [prop for prop in properties if prop.get('city_slug') == target_slug]


def get_premium_property_by_id(properties, property_id):
    for prop in properties:
        if str(prop.get('premium_id')) == str(property_id):
            return prop
    return None


def normalize_email(email):
    return (email or '').strip().lower()


def send_login_otp_email(recipient_email, otp_code):
    msg = Message(
        subject='HimRooms Login Code',
        recipients=[recipient_email],
    )
    msg.body = (
        f"Hello! Your HimRooms secure login code is: {otp_code}\n"
        "Please do not share this code with anyone."
    )
    mail.send(msg)

# 2. Define your routes
@app.route("/")
def home():
    all_properties = load_property_data()
    city_cards = build_city_cards(all_properties)

    return render_template(
        'index.html',
        home_city_cards=city_cards,
        top_city_cards=city_cards[:3],
        home_grid_cards=city_cards[:12],
    )

# --- LOGIN ROUTE ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None
    info_message = request.args.get('info')
    prefill_email = normalize_email(request.args.get('email'))
    
    if request.method == 'POST':
        user_email = normalize_email(request.form.get('email'))
        prefill_email = user_email
        saved_user = get_user_by_email(user_email)

        # Check if the EMAIL exists in our records
        if saved_user:
            # Generate a 6-digit OTP
            otp = str(random.randint(100000, 999999))
            session['otp'] = otp
            session['temp_email'] = user_email
            session['temp_user_key'] = saved_user.email
            
            # Send the Email
            try:
                send_login_otp_email(user_email, otp)
                return redirect(url_for('verify_otp'))
            except Exception as e:
                print(f"OTP email send failed for {user_email}: {str(e)}")

                # Development fallback if SMTP is blocked locally.
                if app.debug:
                    session['debug_otp_preview'] = otp
                    return redirect(url_for('verify_otp', info='Email service unavailable. Use the debug OTP shown below.'))

                error_message = "Failed to send OTP email. Please check MAIL settings and try again."
        else:
            error_message = "This email is not registered. Please register first."
            
    return render_template('login.html', error=error_message, info=info_message, prefill_email=prefill_email)

@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    error_message = None
    info_message = request.args.get('info')

    temp_user_key = session.get('temp_user_key')
    temp_email = session.get('temp_email')
    if not temp_user_key or not temp_email:
        return redirect(url_for('login', info='Please request a new OTP to continue.'))
    
    if request.method == 'POST':
        user_entered_otp = request.form.get('otp')
        
        if user_entered_otp == session.get('otp'):
            # Correct OTP! Log them in.
            saved_user = get_user_by_email(temp_email)
            if not saved_user:
                return redirect(url_for('login', info='User not found. Please login again.'))
            
            session['logged_in'] = True
            session['user_name'] = saved_user.name
            session['user_email'] = temp_email
            session['user_mobile'] = saved_user.mobile
            session['user_city'] = saved_user.city
            session['user_avatar'] = saved_user.avatar
            
            # Clear security variables
            session.pop('otp', None)
            session.pop('temp_email', None)
            session.pop('temp_user_key', None)
            session.pop('debug_otp_preview', None)
            
            try:
                return redirect(url_for(saved_user['city'].lower()))
            except:
                return redirect(url_for('shimla'))
        else:
            error_message = "Invalid OTP. Please try again."
            
    return render_template(
        'verify.html',
        error=error_message,
        info=info_message,
        debug_otp=session.get('debug_otp_preview') if app.debug else None,
    )

# --- REGISTER ROUTE ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    error_message = None

    if request.method == 'POST':
        user_name = request.form.get('name')
        email = normalize_email(request.form.get('email'))
        mobile = request.form.get('mobile')
        city = request.form.get('city')
        avatar = request.form.get('avatar')

        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            error_message = "Invalid email format."
            return render_template('register.html', error=error_message)
        
        if not re.match(r'^[6-9][0-9]{9}$', mobile):
            error_message = "Invalid mobile number. Must be 10 digits starting with 6, 7, 8, or 9."
            return render_template('register.html', error=error_message)

        existing_user = get_user_by_email(email)
        if existing_user:
            error_message = "Email is already registered. Please login instead."
            return render_template('register.html', error=error_message)
        
        avatar_filename = avatar if avatar else 'avatarm.jpg'
        
        user_data = {
            "name": user_name,
            "email": email,
            "mobile": mobile,         # Save mobile inside the data
            "city": city,
            "avatar": avatar_filename
        }
        
        # Save user by normalized email so login lookup remains consistent.
        save_user(user_data)

        return redirect(url_for('login', info='Registration successful. Please login with OTP.', email=email))

    return render_template('register.html', error=error_message)

@app.route('/logout')
def logout():
    # Clears all data from the session
    session.clear()
    return redirect(url_for('home'))

@app.route("/contact", methods=['GET'])
def contact():
    source = (request.args.get('source') or 'unknown').strip()

    user_name = (session.get('user_name') or 'Anonymous Visitor').strip()
    user_email = normalize_email(session.get('user_email') or 'not-provided@himrooms.local')
    user_mobile = (session.get('user_mobile') or 'not-provided').strip()

    request_meta = {
        'source': source,
        'referrer': request.referrer or '',
        'ip': request.headers.get('X-Forwarded-For', request.remote_addr or ''),
        'user_agent': request.headers.get('User-Agent', ''),
    }

    new_contact_log = ContactMessage(
        name=user_name[:100],
        email=user_email[:100],
        phone=user_mobile[:20],
        message=json.dumps(request_meta, ensure_ascii=True)[:1000],
    )
    db.session.add(new_contact_log)
    db.session.commit()

    subject = quote('Inquiry from HimRooms')
    body = quote(
        f"Hello HimRooms Team,\\n\\n"
        f"I would like to know more about your services.\\n\\n"
        f"My details:\\n"
        f"Name: {user_name}\\n"
        f"Email: {user_email if user_email != 'not-provided@himrooms.local' else 'Not provided'}\\n"
        f"Mobile: {user_mobile if user_mobile != 'not-provided' else 'Not provided'}\\n"
    )

    return redirect(f"mailto:dadwalpreeti31@gmail.com?subject={subject}&body={body}")

# Make sure to import session and redirect at the top of your file if you haven't!
# from flask import session, redirect, url_for, request, render_template

# In your main.py create route:
# ==========================================
#        RENT AGREEMENT CREATION ROUTES
# ==========================================

# --- NEW: Route to clear old data and start a fresh agreement ---
@app.route("/new_agreement")
def new_agreement():
    # 1. Check if user is logged in
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    # 2. Clear all old form data but KEEP the user's login details!
    keys_to_keep = ['logged_in', 'user_name', 'user_mobile', 'user_city', 'user_avatar']
    
    # Create a list of keys to delete (everything else)
    keys_to_delete = [key for key in list(session.keys()) if key not in keys_to_keep]
    
    for key in keys_to_delete:
        session.pop(key, None)
        
    # 3. Send them to the fresh first step
    return redirect(url_for('create'))


@app.route("/create", methods=['GET', 'POST'])
def create():
    # SECURITY: Kick out if not logged in
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        session['owner_name'] = request.form.get('owner_name').upper()
        session['owner_mobile'] = request.form.get('owner_mobile')
        session['owner_address'] = request.form.get('owner_address').upper()
        return redirect(url_for('create1')) 
    return render_template('create.html')

@app.route("/create1", methods=['GET', 'POST'])
def create1():
    # SECURITY: Kick out if not logged in
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        session['tenant_name'] = request.form.get('tenant_name').upper()
        session['tenant_mobile'] = request.form.get('tenant_mobile')
        session['tenant_address'] = request.form.get('tenant_address').upper()
        return redirect(url_for('create2')) 
    return render_template('create1.html')

@app.route("/create2", methods=['GET', 'POST'])
def create2():
    # SECURITY: Kick out if not logged in
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        session['prop_state'] = request.form.get('prop_state')
        session['prop_city'] = request.form.get('prop_city')
        session['prop_pincode'] = request.form.get('prop_pincode')
        session['prop_address'] = request.form.get('prop_address').upper()
        return redirect(url_for('create3')) 
    return render_template('create2.html')

@app.route("/create3", methods=['GET', 'POST'])
def create3():
    # SECURITY: Kick out if not logged in
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        session['rent_amount'] = request.form.get('rent_amount')
        session['deposit'] = request.form.get('deposit')
        session['lock_in'] = request.form.get('lock_in')
        session['notice_period'] = request.form.get('notice_period')
        session['validity'] = request.form.get('validity')
        session['start_date'] = request.form.get('start_date')
        session['created_by'] = request.form.get('created_by')
        session['email'] = request.form.get('email')
        return redirect(url_for('create4')) 
    return render_template('create3.html')

@app.route("/create4", methods=['GET', 'POST'])
def create4():
    # SECURITY: Kick out if not logged in
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # GATEKEEPER: Ensure previous steps are done before allowing access to step 5
    required_keys = ['owner_name', 'tenant_name', 'prop_city', 'rent_amount']
    if not all(k in session for k in required_keys):
        return redirect(url_for('create')) 

    if request.method == 'POST':
        # DYNAMIC FURNITURE CAPTURE
        furniture_list = []
        for key in request.form.keys():
            if key.startswith('item_'):
                row_id = key.split('_')[1] 
                item_name = request.form.get(f'item_{row_id}')
                item_qty = request.form.get(f'qty_{row_id}')
                if item_name and item_qty: 
                    furniture_list.append({"item": item_name.title(), "qty": item_qty})
        session['furniture_data'] = json.dumps(furniture_list)

        # SAVE TO SQLITE DATABASE
        new_agreement = RentAgreement(
            owner_name=session.get('owner_name'),
            owner_mobile=session.get('owner_mobile'),
            owner_address=session.get('owner_address'),
            tenant_name=session.get('tenant_name'),
            tenant_mobile=session.get('tenant_mobile'),
            tenant_address=session.get('tenant_address'),
            prop_city=session.get('prop_city'),
            prop_address=session.get('prop_address'),
            prop_pincode=session.get('prop_pincode'),
            rent_amount=session.get('rent_amount'),
            deposit=session.get('deposit'),
            validity=session.get('validity'),
            start_date=session.get('start_date')
        )
        db.session.add(new_agreement)
        db.session.commit()
        
        session['agreement_finalized'] = True
        return redirect(url_for('generate_agreement'))

    return render_template('create4.html')

@app.route("/generate_agreement")
def generate_agreement():
    # SECURITY: Kick out if not logged in
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # Safety check. Don't show the final doc if they didn't hit 'Submit' on page 4
    if not session.get('agreement_finalized'):
        return redirect(url_for('create4'))
        
    return render_template('final_agreement.html')

@app.route("/premium")
def premium(): 
    all_premium = enrich_premium_properties(load_premium_data())
    cities = extract_premium_cities(all_premium)

    requested_city_slug = slugify(request.args.get('city', ''))
    supported_city_slugs = {city['slug'] for city in cities}

    if requested_city_slug in supported_city_slugs:
        active_city_slug = requested_city_slug
    elif cities:
        active_city_slug = cities[0]['slug']
    else:
        active_city_slug = ''

    listings = filter_premium_by_city_slug(all_premium, active_city_slug)
    active_city_name = next(
        (city['name'] for city in cities if city['slug'] == active_city_slug),
        'Premium'
    )

    return render_template(
        'premium.html',
        listings=listings,
        cities=cities,
        active_city_slug=active_city_slug,
        active_city_name=active_city_name,
    )

@app.route("/premium1")
def premium1(): 
    return redirect(url_for('premium', city='dharamshala'))

@app.route("/premium2")
def premium2(): 
    return redirect(url_for('premium', city='manali'))

@app.route("/premium3")
def premium3(): 
    return redirect(url_for('premium', city='kullu'))


@app.route('/premium/property/<int:property_id>')
def premium_property_detail(property_id):
    all_premium = enrich_premium_properties(load_premium_data())
    target_property = get_premium_property_by_id(all_premium, property_id)

    if not target_property:
        abort(404)

    gallery_images = target_property.get('images') or []

    return render_template(
        'premium_property_details.html',
        property=target_property,
        gallery_images=gallery_images,
    )

@app.route('/premium/book/<int:property_id>', methods=['GET', 'POST'])
@app.route("/premium4", methods=['GET', 'POST'])
def premium4(property_id=None):
    all_premium = enrich_premium_properties(load_premium_data())
    success_message = None

    # Keep old /premium4?property=... links working while new pages use property_id.
    if property_id is None:
        query_title = (request.args.get('property') or '').strip().lower()
        if query_title:
            for prop in all_premium:
                if (prop.get('title') or '').strip().lower() == query_title:
                    property_id = prop.get('premium_id')
                    break

    target_property = get_premium_property_by_id(all_premium, property_id) if property_id else None
    if not target_property:
        abort(404)

    property_title = target_property.get('title', 'Unknown Property')

    if request.method == 'POST':
        if not session.get('logged_in'):
            return redirect(url_for('login'))

        visitor_name = request.form.get('name').upper()
        visitor_mobile = request.form.get('mobile')
        visit_date = request.form.get('visit_datetime')

        new_visit = VisitRequest(
            property_title=property_title,
            name=visitor_name,
            mobile=visitor_mobile,
            visit_datetime=visit_date
        )
        db.session.add(new_visit)
        db.session.commit()

        success_message = "Visit successfully booked! The property owner will contact you shortly regarding this request."

    return render_template(
        'premium4.html',
        success_message=success_message,
        property_title=property_title,
        property_id=target_property.get('premium_id'),
    )

@app.route("/apply", methods=['GET', 'POST'])
def apply():
    all_properties = load_property_data()
    city_options = extract_supported_cities(all_properties)
    allowed_city_slugs = {city['slug'] for city in city_options}
    allowed_user_types = {'Tenant', 'Owner', 'Broker'}

    form_data = {
        'first_name': '',
        'last_name': '',
        'mobile': '',
        'email': '',
        'city': '',
        'user_type': '',
    }
    success_message = None
    error_message = None

    if request.method == 'POST':
        form_data = {
            'first_name': (request.form.get('first_name') or '').strip(),
            'last_name': (request.form.get('last_name') or '').strip(),
            'mobile': (request.form.get('mobile') or '').strip(),
            'email': normalize_email(request.form.get('email') or ''),
            'city': (request.form.get('city') or '').strip(),
            'user_type': (request.form.get('user_type') or '').strip(),
        }

        if not request.form.get('terms_accepted'):
            error_message = "Please accept terms & conditions to continue."
        elif not re.match(r'^[A-Za-z][A-Za-z\s\.-]{1,49}$', form_data['first_name']):
            error_message = "Please enter a valid first name."
        elif form_data['last_name'] and not re.match(r'^[A-Za-z][A-Za-z\s\.-]{1,49}$', form_data['last_name']):
            error_message = "Please enter a valid last name."
        elif not re.match(r'^[6-9][0-9]{9}$', form_data['mobile']):
            error_message = "Please enter a valid 10-digit mobile number starting with 6, 7, 8, or 9."
        elif not re.fullmatch(
            r'^(?=.{6,254}$)(?=.{1,64}@)[A-Za-z0-9](?:[A-Za-z0-9._%+-]{0,62}[A-Za-z0-9])?@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,24}$',
            form_data['email']
        ):
            error_message = "Please enter a valid email address."
        elif '..' in form_data['email'] or form_data['email'].startswith('.') or form_data['email'].endswith('.'):
            error_message = "Please enter a valid email address."
        elif slugify(form_data['city']) not in allowed_city_slugs:
            error_message = "Please choose a city from the available list only."
        elif form_data['user_type'] not in allowed_user_types:
            error_message = "Please select whether you are Tenant, Owner, or Broker."
        else:
            normalized_city_slug = slugify(form_data['city'])
            normalized_city_name = next(
                (city['name'] for city in city_options if city['slug'] == normalized_city_slug),
                form_data['city'].title()
            )

            new_interest = ApplyInterest(
                first_name=form_data['first_name'].title(),
                last_name=form_data['last_name'].title(),
                mobile=form_data['mobile'],
                email=form_data['email'],
                city=normalized_city_name,
                user_type=form_data['user_type'],
            )
            db.session.add(new_interest)
            db.session.commit()

            success_message = "Interest submitted successfully. We will contact you shortly on your email and mobile number."
            form_data = {
                'first_name': '',
                'last_name': '',
                'mobile': '',
                'email': '',
                'city': '',
                'user_type': '',
            }

    return render_template(
        'apply.html',
        city_options=city_options,
        form_data=form_data,
        success=success_message,
        error=error_message,
    )

@app.route("/cities")
def cities():
    all_properties = load_property_data()
    cards = build_city_cards(all_properties)

    return render_template('cities.html', city_cards=cards)

@app.route("/company")
def company():
    return render_template('company.html')

@app.route("/terms")
def terms():
    return render_template('terms.html')

@app.route("/privacy")
def privacy():
    return render_template('privacy.html')

@app.route("/refund")
def refund():
    return render_template('refund.html')

@app.route("/reqver", methods=['GET', 'POST'])
def reqver():
    success_message = None
    error_message = None

    if request.method == 'POST':
        # 1. Grab text data
        name = request.form.get('name')
        mobile = request.form.get('mobile')
        email = request.form.get('email')
        
        # Grab all checked checkboxes (returns a list of values)
        services = request.form.getlist('service') 
        services_str = ", ".join(services)

        # 2. Basic Validation
        if not re.match(r'^[6-9][0-9]{9}$', mobile):
            error_message = "Invalid mobile number."
            return render_template('reqver.html', error=error_message)

        # 3. Handle File Uploads (Aadhaar Front and Back)
        front_file = request.files.get('aadhaar-front')
        back_file = request.files.get('aadhaar-back')

        front_filename = ""
        back_filename = ""

        if front_file and front_file.filename != '':
            front_filename = secure_filename(front_file.filename)
            front_file.save(os.path.join(app.config['UPLOAD_FOLDER'], front_filename))
            
        if back_file and back_file.filename != '':
            back_filename = secure_filename(back_file.filename)
            back_file.save(os.path.join(app.config['UPLOAD_FOLDER'], back_filename))

        # 4. Save to Database
        new_request = VerificationRequest(
            name=name,
            mobile=mobile,
            email=email,
            aadhaar_front_filename=front_filename,
            aadhaar_back_filename=back_filename,
            services_requested=services_str
        )
        db.session.add(new_request)
        db.session.commit()

        success_message = "Your verification request has been successfully submitted! We will contact you shortly."

    return render_template('reqver.html', success=success_message, error=error_message)

@app.route("/rent_rec", methods=['GET', 'POST'])
def rent_rec():
    error_message = None
    receipt_data = None # We will pass this back to HTML if successful

    if request.method == 'POST':
        # 1. Grab data from the form
        rent_amount = request.form.get('rentAmount')
        prop_address = request.form.get('propAddress')
        landlord_name = request.form.get('landlordName')
        landlord_pan = request.form.get('landlordPan', 'Not Provided')
        start_date = request.form.get('startDate')
        months = request.form.get('months')
        tenant_name = request.form.get('tenantName')
        tenant_mobile = request.form.get('tenantMobile')
        tenant_email = request.form.get('tenantEmail')

        # 2. Server-side Validation
        if not re.match(r'^[6-9][0-9]{9}$', tenant_mobile):
            error_message = "Invalid mobile number. Must be 10 digits starting with 6, 7, 8, or 9."
            return render_template('rent_rec.html', error=error_message)

        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', tenant_email):
            error_message = "Invalid email format."
            return render_template('rent_rec.html', error=error_message)

        # 3. Save to Database
        new_receipt = RentReceipt(
            rent_amount=int(rent_amount),
            prop_address=prop_address,
            landlord_name=landlord_name,
            landlord_pan=landlord_pan,
            start_date=start_date,
            months=int(months),
            tenant_name=tenant_name,
            tenant_mobile=tenant_mobile,
            tenant_email=tenant_email
        )
        db.session.add(new_receipt)
        db.session.commit()

        # 4. Package the data to send back to the frontend to generate the tab
        receipt_data = {
            "rentAmount": rent_amount,
            "propAddress": prop_address,
            "landlordName": landlord_name,
            "landlordPan": landlord_pan,
            "startDate": start_date,
            "months": months,
            "tenantName": tenant_name,
            "tenantMobile": tenant_mobile,
            "tenantEmail": tenant_email,
            "totalRent": int(rent_amount) * int(months)
        }

    return render_template('rent_rec.html', error=error_message, receipt_data=receipt_data)

@app.route("/manage_flat")
def manage_flat():
    return render_template('manage_flat.html')

@app.route("/manage_apply")
def manage_apply():
    return render_template('manage_apply.html')


@app.route('/city/<city_slug>')
def city_listings(city_slug):
    all_properties = load_property_data()
    cities = extract_supported_cities(all_properties)
    resolved_slug = resolve_city_slug(city_slug, all_properties)
    city_name = get_city_name_by_slug(resolved_slug, all_properties)
    listings = filter_properties_by_slug(all_properties, resolved_slug)

    return render_template(
        'city_listings.html',
        listings=listings,
        city_name=city_name,
        city_slug=resolved_slug,
        active_category='all',
        cities=cities,
    )


@app.route('/city/<city_slug>/<category>')
def city_category_listings(city_slug, category):
    valid_categories = {'rooms', 'roommates', 'pg'}
    if category not in valid_categories:
        abort(404)

    all_properties = load_property_data()
    cities = extract_supported_cities(all_properties)
    resolved_slug = resolve_city_slug(city_slug, all_properties)
    city_name = get_city_name_by_slug(resolved_slug, all_properties)
    listings = filter_properties_by_slug(all_properties, resolved_slug, category)

    return render_template(
        'city_listings.html',
        listings=listings,
        city_name=city_name,
        city_slug=resolved_slug,
        active_category=category,
        cities=cities,
    )

@app.route("/shimla")
def shimla():
    return redirect(url_for('city_listings', city_slug='shimla'))

@app.route("/shimla_rooms")
def shimla_rooms():
    return redirect(url_for('city_category_listings', city_slug='shimla', category='rooms'))

@app.route("/shimla_rooms1")
def shimla_rooms1():
    return redirect(url_for('city_category_listings', city_slug='shimla', category='roommates'))

@app.route("/shimla_rooms2")
def shimla_rooms2():
    return redirect(url_for('city_category_listings', city_slug='shimla', category='pg'))

# ==========================================
#         DHARAMSHALA ROUTES
# ==========================================

@app.route("/dharamshala")
def dharamshala():
    return redirect(url_for('city_listings', city_slug='dharamshala'))

@app.route("/dharamshala_rooms")
def dharamshala_rooms():
    return redirect(url_for('city_category_listings', city_slug='dharamshala', category='rooms'))

@app.route("/dharamshala_rooms1")
def dharamshala_rooms1():
    return redirect(url_for('city_category_listings', city_slug='dharamshala', category='roommates'))

@app.route("/dharamshala_rooms2")
def dharamshala_rooms2():
    return redirect(url_for('city_category_listings', city_slug='dharamshala', category='pg'))

# ==========================================
#             MANALI ROUTES
# ==========================================

@app.route("/manali")
def manali():
    return redirect(url_for('city_listings', city_slug='manali'))

@app.route("/manali_rooms")
def manali_rooms():
    return redirect(url_for('city_category_listings', city_slug='manali', category='rooms'))

@app.route("/manali_rooms1")
def manali_rooms1():
    return redirect(url_for('city_category_listings', city_slug='manali', category='roommates'))

@app.route("/manali_rooms2")
def manali_rooms2():
    return redirect(url_for('city_category_listings', city_slug='manali', category='pg'))

@app.route("/property/<property_id>")
def property_detail(property_id):
    """
    Fetch details for a specific property card and render the detail page.
    """
    all_properties = load_property_data()
    
    target_property = None
    for prop in all_properties:
        # Convert both IDs to strings to ensure they match (Integer 1 vs String "1")
        if str(prop.get('id')) == str(property_id):
            target_property = prop
            break

    # If no property matches, show the 404 error
    if not target_property:
        abort(404)

    gallery_images = target_property.get('images') or ['images/avatarm.jpg']
    city_name, city_slug = resolve_property_city(target_property.get('location'))

    return render_template(
        'property_details.html',
        property=target_property,
        cover_image=gallery_images[0],
        gallery_images=gallery_images,
        city_name=city_name,
        city_slug=city_slug,
    )

# 3. Start the server
if __name__ == "__main__":
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode)