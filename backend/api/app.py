from flask import Flask
from flask_cors import CORS # Import CORS
# Assuming your routes are defined in 'routes.py' within the same 'api' package
from .routes import api_bp
# from config import settings # You might use this later for configurations

def create_app():
    """
    Factory function to create and configure the Flask application.
    """
    app = Flask(__name__)
    CORS(app) # Enable CORS for all routes

    # Register the Blueprint from routes.py
    # All routes defined in api_bp will be prefixed with /api
    # So, the '/search' route in routes.py will become '/api/search'
    app.register_blueprint(api_bp, url_prefix='/api')

    # Example: Load configurations if you have them
    # app.config.from_object(settings)

    return app

if __name__ == '__main__':
    # This block runs when the script is executed directly (e.g., python app.py)
    # It's suitable for local development.
    # For production, you would typically use a WSGI server like Gunicorn or uWSGI.
    app = create_app()
    # Running on 0.0.0.0 makes the server accessible externally (be careful in untrusted networks)
    # debug=True enables Flask's debugger and auto-reloader, which is useful for development.
    app.run(debug=True, host='0.0.0.0', port=5000)
