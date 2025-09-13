"""
Database models for the Church Website
"""

import sqlite3
from contextlib import contextmanager
from flask import current_app

@contextmanager
def get_db():
    """Database connection context manager"""
    conn = sqlite3.connect(current_app.config['DATABASE'])
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
