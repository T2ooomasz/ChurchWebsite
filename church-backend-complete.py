"""
Complete Flask Backend for Church Website
File: app.py
"""

import os
import json
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import re
from contextlib import contextmanager

# ============================================
# Configuration
# ============================================

class Config:
    """Application configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DATABASE = os.environ.get('DATABASE') or 'church.db'
    
    # Flask-Mail configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', '1', 'yes']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'info@gracecommunitychurch.org'
    
    # CORS settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5000').split(',')
    
    # Admin credentials (change in production)
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'admin123'
    
    # Rate limiting
    RATE_LIMIT_ENABLED = os.environ.get('RATE_LIMIT_ENABLED', 'true').lower() in ['true', '1', 'yes']
    RATE_LIMIT_REQUESTS = int(os.environ.get('RATE_LIMIT_REQUESTS') or 100)
    RATE_LIMIT_PERIOD = int(os.environ.get('RATE_LIMIT_PERIOD') or 3600)  # seconds

# ============================================
# Application Setup
# ============================================

app = Flask(__name__)
app.config.from_object(Config)

# Setup CORS
CORS(app, origins=app.config['CORS_ORIGINS'], supports_credentials=True)

# Setup Mail
mail = Mail(app)

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('church_app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================
# Database Setup and Models
# ============================================

@contextmanager
def get_db():
    """Database connection context manager"""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize database with tables"""
    with get_db() as conn:
        conn.executescript('''
            -- Events table
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                date DATE NOT NULL,
                time TEXT,
                location TEXT,
                image_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_events_date ON events(date);
            
            -- Services table
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day TEXT NOT NULL,
                time TEXT NOT NULL,
                type TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Contact submissions table
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                subject TEXT,
                message TEXT NOT NULL,
                date_submitted TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email);
            
            -- Prayer requests table
            CREATE TABLE IF NOT EXISTS prayer_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                request TEXT NOT NULL,
                is_anonymous BOOLEAN DEFAULT 0,
                date_submitted TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Announcements table
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                date_posted TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expiry_date DATE,
                is_active BOOLEAN DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS idx_announcements_date ON announcements(date_posted);
            
            -- Newsletter subscriptions table
            CREATE TABLE IF NOT EXISTS newsletter (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                date_subscribed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS idx_newsletter_email ON newsletter(email);
            
            -- Rate limiting table
            CREATE TABLE IF NOT EXISTS rate_limits (
                ip_address TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (ip_address, endpoint, timestamp)
            );
            
            -- Insert sample data
            INSERT OR IGNORE INTO events (title, description, date, time, location) VALUES
                ('Community Outreach', 'Join us as we serve our local community with food and fellowship.', '2024-12-15', '10:00 AM', 'Church Parking Lot'),
                ('Christmas Eve Service', 'Celebrate the birth of Christ with candlelight and carols.', '2024-12-24', '7:00 PM', 'Main Sanctuary'),
                ('Youth Winter Retreat', 'A weekend of fun, fellowship, and spiritual growth for teens.', '2025-01-10', '6:00 PM', 'Mountain View Camp'),
                ('New Year Prayer Meeting', 'Start the year with prayer and worship.', '2025-01-01', '10:00 PM', 'Prayer Room');
            
            INSERT OR IGNORE INTO services (day, time, type, description) VALUES
                ('Sunday', '9:00 AM', 'Traditional', 'Traditional worship with hymns and organ music'),
                ('Sunday', '11:00 AM', 'Contemporary', 'Modern worship with contemporary music'),
                ('Wednesday', '7:00 PM', 'Bible Study', 'Mid-week Bible study and prayer meeting'),
                ('Sunday', '10:00 AM', 'Sunday School', 'Classes for all ages');
            
            INSERT OR IGNORE INTO announcements (title, content, expiry_date) VALUES
                ('Welcome to Our New Website!', 'We are excited to launch our new church website. Explore all the features and stay connected!', '2024-12-31'),
                ('Christmas Schedule', 'Join us for special Christmas services throughout December. Check our events page for details.', '2024-12-26');
        ''')
        conn.commit()

# ============================================
# Helper Functions and Decorators
# ============================================

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}
    return re.match(pattern, email) is not None

def sanitize_input(text):
    """Sanitize user input to prevent XSS"""
    if text is None:
        return None
    # Remove any HTML tags
    clean = re.sub('<.*?>', '', str(text))
    # Escape special characters
    clean = clean.replace('&', '&amp;')
    clean = clean.replace('<', '&lt;')
    clean = clean.replace('>', '&gt;')
    clean = clean.replace('"', '&quot;')
    clean = clean.replace("'", '&#x27;')
    return clean

def rate_limit(endpoint_name):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not app.config['RATE_LIMIT_ENABLED']:
                return f(*args, **kwargs)
            
            ip_address = request.remote_addr
            current_time = datetime.now()
            time_window = current_time - timedelta(seconds=app.config['RATE_LIMIT_PERIOD'])
            
            with get_db() as conn:
                # Clean old entries
                conn.execute('DELETE FROM rate_limits WHERE timestamp < ?', (time_window,))
                
                # Count recent requests
                count = conn.execute(
                    'SELECT COUNT(*) FROM rate_limits WHERE ip_address = ? AND endpoint = ? AND timestamp > ?',
                    (ip_address, endpoint_name, time_window)
                ).fetchone()[0]
                
                if count >= app.config['RATE_LIMIT_REQUESTS']:
                    return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
                
                # Log this request
                conn.execute(
                    'INSERT INTO rate_limits (ip_address, endpoint, timestamp) VALUES (?, ?, ?)',
                    (ip_address, endpoint_name, current_time)
                )
                conn.commit()
            
            return f(*args, **kwargs)
        return wrapped
    return decorator

def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({'error': 'Admin authentication required'}), 401
        return f(*args, **kwargs)
    return wrapped

# ============================================
# API Routes - Events
# ============================================

@app.route('/api/events', methods=['GET', 'POST'])
def handle_events():
    """Get all events or create new event (admin only for POST)"""
    if request.method == 'GET':
        try:
            with get_db() as conn:
                # Get upcoming events
                events = conn.execute(
                    'SELECT * FROM events WHERE date >= date("now") ORDER BY date, time LIMIT 50'
                ).fetchall()
                
                return jsonify([dict(event) for event in events])
        except Exception as e:
            logger.error(f"Error fetching events: {e}")
            return jsonify({'error': 'Failed to fetch events'}), 500
    
    else:  # POST
        if not session.get('is_admin'):
            return jsonify({'error': 'Admin authentication required'}), 401
        
        try:
            data = request.json
            title = sanitize_input(data.get('title'))
            description = sanitize_input(data.get('description'))
            date = data.get('date')
            time = sanitize_input(data.get('time'))
            location = sanitize_input(data.get('location'))
            image_url = sanitize_input(data.get('image_url'))
            
            if not title or not date:
                return jsonify({'error': 'Title and date are required'}), 400
            
            with get_db() as conn:
                cursor = conn.execute(
                    'INSERT INTO events (title, description, date, time, location, image_url) VALUES (?, ?, ?, ?, ?, ?)',
                    (title, description, date, time, location, image_url)
                )
                conn.commit()
                
                return jsonify({'id': cursor.lastrowid, 'message': 'Event created successfully'}), 201
        except Exception as e:
            logger.error(f"Error creating event: {e}")
            return jsonify({'error': 'Failed to create event'}), 500

@app.route('/api/events/<int:event_id>', methods=['GET', 'PUT', 'DELETE'])
def handle_event(event_id):
    """Get, update, or delete specific event"""
    if request.method == 'GET':
        try:
            with get_db() as conn:
                event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
                if event:
                    return jsonify(dict(event))
                return jsonify({'error': 'Event not found'}), 404
        except Exception as e:
            logger.error(f"Error fetching event {event_id}: {e}")
            return jsonify({'error': 'Failed to fetch event'}), 500
    
    elif request.method == 'PUT':
        if not session.get('is_admin'):
            return jsonify({'error': 'Admin authentication required'}), 401
        
        try:
            data = request.json
            with get_db() as conn:
                conn.execute(
                    'UPDATE events SET title=?, description=?, date=?, time=?, location=?, image_url=?, updated_at=CURRENT_TIMESTAMP WHERE id=?',
                    (sanitize_input(data.get('title')), sanitize_input(data.get('description')),
                     data.get('date'), sanitize_input(data.get('time')),
                     sanitize_input(data.get('location')), sanitize_input(data.get('image_url')), event_id)
                )
                conn.commit()
                return jsonify({'message': 'Event updated successfully'})
        except Exception as e:
            logger.error(f"Error updating event {event_id}: {e}")
            return jsonify({'error': 'Failed to update event'}), 500
    
    else:  # DELETE
        if not session.get('is_admin'):
            return jsonify({'error': 'Admin authentication required'}), 401
        
        try:
            with get_db() as conn:
                conn.execute('DELETE FROM events WHERE id = ?', (event_id,))
                conn.commit()
                return jsonify({'message': 'Event deleted successfully'})
        except Exception as e:
            logger.error(f"Error deleting event {event_id}: {e}")
            return jsonify({'error': 'Failed to delete event'}), 500

# ============================================
# API Routes - Services
# ============================================

@app.route('/api/services', methods=['GET', 'POST'])
def handle_services():
    """Get or update service times"""
    if request.method == 'GET':
        try:
            with get_db() as conn:
                services = conn.execute('SELECT * FROM services ORDER BY id').fetchall()
                return jsonify([dict(service) for service in services])
        except Exception as e:
            logger.error(f"Error fetching services: {e}")
            return jsonify({'error': 'Failed to fetch services'}), 500
    
    else:  # POST (admin only)
        if not session.get('is_admin'):
            return jsonify({'error': 'Admin authentication required'}), 401
        
        try:
            data = request.json
            with get_db() as conn:
                cursor = conn.execute(
                    'INSERT INTO services (day, time, type, description) VALUES (?, ?, ?, ?)',
                    (sanitize_input(data.get('day')), sanitize_input(data.get('time')),
                     sanitize_input(data.get('type')), sanitize_input(data.get('description')))
                )
                conn.commit()
                return jsonify({'id': cursor.lastrowid, 'message': 'Service time added successfully'}), 201
        except Exception as e:
            logger.error(f"Error adding service: {e}")
            return jsonify({'error': 'Failed to add service'}), 500

# ============================================
# API Routes - Contact & Prayer Requests
# ============================================

@app.route('/api/contact', methods=['POST'])
@rate_limit('contact')
def handle_contact():
    """Submit contact form"""
    try:
        data = request.json
        name = sanitize_input(data.get('name'))
        email = data.get('email')
        subject = sanitize_input(data.get('subject'))
        message = sanitize_input(data.get('message'))
        
        # Validation
        if not all([name, email, message]):
            return jsonify({'error': 'Name, email, and message are required'}), 400
        
        if not validate_email(email):
            return jsonify({'error': 'Invalid email address'}), 400
        
        with get_db() as conn:
            conn.execute(
                'INSERT INTO contacts (name, email, subject, message) VALUES (?, ?, ?, ?)',
                (name, email, subject, message)
            )
            conn.commit()
        
        # Send email notification (if configured)
        try:
            if app.config['MAIL_USERNAME']:
                msg = Message(
                    f'New Contact Form Submission: {subject or "No Subject"}',
                    recipients=['info@gracecommunitychurch.org'],
                    body=f'From: {name} ({email})\n\nMessage:\n{message}'
                )
                mail.send(msg)
        except Exception as e:
            logger.warning(f"Failed to send email notification: {e}")
        
        return jsonify({'message': 'Contact form submitted successfully'}), 201
    except Exception as e:
        logger.error(f"Error submitting contact form: {e}")
        return jsonify({'error': 'Failed to submit contact form'}), 500

@app.route('/api/prayer-requests', methods=['POST'])
@rate_limit('prayer')
def handle_prayer_request():
    """Submit prayer request"""
    try:
        data = request.json
        name = sanitize_input(data.get('name'))
        email = data.get('email')
        request_text = sanitize_input(data.get('request'))
        is_anonymous = data.get('is_anonymous', False)
        
        if not request_text:
            return jsonify({'error': 'Prayer request is required'}), 400
        
        if email and not validate_email(email):
            return jsonify({'error': 'Invalid email address'}), 400
        
        with get_db() as conn:
            conn.execute(
                'INSERT INTO prayer_requests (name, email, request, is_anonymous) VALUES (?, ?, ?, ?)',
                (name if not is_anonymous else None, email, request_text, is_anonymous)
            )
            conn.commit()
        
        return jsonify({'message': 'Prayer request submitted successfully'}), 201
    except Exception as e:
        logger.error(f"Error submitting prayer request: {e}")
        return jsonify({'error': 'Failed to submit prayer request'}), 500

# ============================================
# API Routes - Announcements & Newsletter
# ============================================

@app.route('/api/announcements', methods=['GET', 'POST'])
def handle_announcements():
    """Get announcements or create new (admin only for POST)"""
    if request.method == 'GET':
        try:
            with get_db() as conn:
                announcements = conn.execute(
                    'SELECT * FROM announcements WHERE is_active = 1 AND (expiry_date IS NULL OR expiry_date >= date("now")) ORDER BY date_posted DESC LIMIT 10'
                ).fetchall()
                return jsonify([dict(ann) for ann in announcements])
        except Exception as e:
            logger.error(f"Error fetching announcements: {e}")
            return jsonify({'error': 'Failed to fetch announcements'}), 500
    
    else:  # POST
        if not session.get('is_admin'):
            return jsonify({'error': 'Admin authentication required'}), 401
        
        try:
            data = request.json
            title = sanitize_input(data.get('title'))
            content = sanitize_input(data.get('content'))
            expiry_date = data.get('expiry_date')
            
            if not title or not content:
                return jsonify({'error': 'Title and content are required'}), 400
            
            with get_db() as conn:
                cursor = conn.execute(
                    'INSERT INTO announcements (title, content, expiry_date) VALUES (?, ?, ?)',
                    (title, content, expiry_date)
                )
                conn.commit()
                return jsonify({'id': cursor.lastrowid, 'message': 'Announcement created successfully'}), 201
        except Exception as e:
            logger.error(f"Error creating announcement: {e}")
            return jsonify({'error': 'Failed to create announcement'}), 500

@app.route('/api/newsletter', methods=['POST'])
@rate_limit('newsletter')
def handle_newsletter():
    """Subscribe to newsletter"""
    try:
        data = request.json
        email = data.get('email')
        
        if not email or not validate_email(email):
            return jsonify({'error': 'Valid email address is required'}), 400
        
        with get_db() as conn:
            # Check if already subscribed
            existing = conn.execute('SELECT * FROM newsletter WHERE email = ?', (email,)).fetchone()
            
            if existing:
                if existing['is_active']:
                    return jsonify({'message': 'Email already subscribed'}), 200
                else:
                    # Reactivate subscription
                    conn.execute('UPDATE newsletter SET is_active = 1 WHERE email = ?', (email,))
                    conn.commit()
                    return jsonify({'message': 'Subscription reactivated successfully'}), 200
            else:
                conn.execute('INSERT INTO newsletter (email) VALUES (?)', (email,))
                conn.commit()
                return jsonify({'message': 'Successfully subscribed to newsletter'}), 201
    except Exception as e:
        logger.error(f"Error subscribing to newsletter: {e}")
        return jsonify({'error': 'Failed to subscribe to newsletter'}), 500

# ============================================
# Admin Authentication
# ============================================

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Admin login endpoint"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if username == app.config['ADMIN_USERNAME'] and password == app.config['ADMIN_PASSWORD']:
            session['is_admin'] = True
            return jsonify({'message': 'Login successful'}), 200
        
        return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        logger.error(f"Error during admin login: {e}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    """Admin logout endpoint"""
    session.pop('is_admin', None)
    return jsonify({'message': 'Logout successful'}), 200

# ============================================
# Error Handlers
# ============================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# ============================================
# Main Application Entry Point
# ============================================

if __name__ == '__main__':
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Run application
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=os.environ.get('FLASK_ENV') == 'development'
    )