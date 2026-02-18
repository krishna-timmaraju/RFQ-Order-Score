"""
TrustMarket API - Lead Scoring Service
Main Flask Application
"""
import os
from flask import Flask, jsonify, Response
from flask_cors import CORS
from config import Config
from api.routes.rfqs import rfqs_bp

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Static folder for UI (resolve relative to this file so /ui works from any cwd)
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')

# Allow same-origin and common dev origins (use API_PORT from config so URL always matches)
_api_port = Config.API_PORT
_allowed_origins = [
    f"http://localhost:{_api_port}",
    f"http://127.0.0.1:{_api_port}",
    "http://localhost:3000",
    "http://localhost:3001",
]
CORS(app, resources={
    r"/api/*": {
        "origins": _allowed_origins,
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type"],
        "supports_credentials": False,
    },
    r"/ui": {"origins": _allowed_origins},
})

# Register blueprints
app.register_blueprint(rfqs_bp, url_prefix='/api')


@app.route('/ui')
def ui():
    """Serve the RFQ Lead Scores web UI (read file directly to avoid 403 from static serving)"""
    index_path = os.path.join(STATIC_DIR, 'index.html')
    if not os.path.isfile(index_path):
        return jsonify({'error': 'UI not found'}), 404
    with open(index_path, 'r', encoding='utf-8') as f:
        html = f.read()
    return Response(html, mimetype='text/html; charset=utf-8')


@app.route('/')
def index():
    """Root endpoint"""
    return jsonify({
        'service': 'TrustMarket Lead Scoring API',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'health': '/api/health',
            'scored_rfqs': '/api/rfqs/scored',
            'rfq_score': '/api/rfqs/<rfq_id>/score',
            'stats': '/api/rfqs/stats',
            'distribution': '/api/rfqs/score-distribution'
        }
    })


@app.errorhandler(404)
def not_found(error):
    """404 error handler"""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """500 error handler"""
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


if __name__ == '__main__':
    print("=" * 60)
    print(f"\n  → Open the UI in your browser: http://localhost:{Config.API_PORT}/ui")
    print("=" * 60)
    print(f"Debug: {Config.DEBUG}")
    print(f"Database: {Config.DB_NAME}@{Config.DB_HOST}")
    print("=" * 60)
    
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule}")
    app.run(
        host=Config.API_HOST,
        port=Config.API_PORT,
        debug=Config.DEBUG
    )