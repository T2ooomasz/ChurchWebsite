"""
Main Flask Application for the Church Website
"""

import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from flask_mail import Mail

from .config import Config
from .models import init_db
from .routes import api

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Setup CORS
    CORS(app, origins=app.config['CORS_ORIGINS'], supports_credentials=True)

    # Setup Mail
    mail = Mail(app)
    app.extensions["mail"] = mail

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

    # Initialize database
    with app.app_context():
        init_db()
        logger.info("Database initialized")

    # Register blueprint
    app.register_blueprint(api, url_prefix='/api')

    # Error Handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Resource not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({'error': 'Internal server error'}), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=os.environ.get('FLASK_ENV') == 'development'
    )
