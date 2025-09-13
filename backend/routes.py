"""
API Routes for the Church Website
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
import re
import logging
from datetime import datetime, timedelta

from .models import get_db

api = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
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
            from flask import current_app
            if not current_app.config['RATE_LIMIT_ENABLED']:
                return f(*args, **kwargs)
            
            ip_address = request.remote_addr
            current_time = datetime.now()
            time_window = current_time - timedelta(seconds=current_app.config['RATE_LIMIT_PERIOD'])
            
            with get_db() as conn:
                # Clean old entries
                conn.execute('DELETE FROM rate_limits WHERE timestamp < ?', (time_window,))
                
                # Count recent requests
                count = conn.execute(
                    'SELECT COUNT(*) FROM rate_limits WHERE ip_address = ? AND endpoint = ? AND timestamp > ?',
                    (ip_address, endpoint_name, time_window)
                ).fetchone()[0]
                
                if count >= current_app.config['RATE_LIMIT_REQUESTS']:
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

@api.route('/events', methods=['GET', 'POST'])
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

@api.route('/events/<int:event_id>', methods=['GET', 'PUT', 'DELETE'])
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

@api.route('/services', methods=['GET', 'POST'])
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

@api.route('/contact', methods=['POST'])
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
            from flask_mail import Message
            from flask import current_app
            mail = current_app.extensions.get('mail')
            if mail and current_app.config['MAIL_USERNAME']:
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

@api.route('/prayer-requests', methods=['POST'])
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

@api.route('/announcements', methods=['GET', 'POST'])
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

@api.route('/newsletter', methods=['POST'])
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

@api.route('/admin/login', methods=['POST'])
def admin_login():
    """Admin login endpoint"""
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        
        if username == session.get('ADMIN_USERNAME') and password == session.get('ADMIN_PASSWORD'):
            session['is_admin'] = True
            return jsonify({'message': 'Login successful'}), 200
        
        return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        logger.error(f"Error during admin login: {e}")
        return jsonify({'error': 'Login failed'}), 500

@api.route('/admin/logout', methods=['POST'])
def admin_logout():
    """Admin logout endpoint"""
    session.pop('is_admin', None)
    return jsonify({'message': 'Logout successful'}), 200
