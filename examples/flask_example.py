#!/usr/bin/env python3
"""
Flask integration example for SyckSec Community Edition
Demonstrates how to integrate SyckSec with Flask applications
"""

from flask import Flask, request, jsonify, g
from functools import wraps
import json
import time

from sycksec import create_client, SyckSec, SyckSecConfig
from sycksec.integrations.flask_middleware import create_sycksec_app, sycksec_required
from sycksec.utils.exceptions import TokenValidationError

def create_example_app():
    """Create Flask app with SyckSec integration"""
    print("🌶️ SyckSec + Flask Integration Example")
    print("=" * 43)
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'flask-example-secret-key'
    
    # Initialize SyckSec with the app
    sycksec_client = create_sycksec_app(app, master_secret="flask-sycksec-secret-32-chars!!")
    
    print("✅ Flask app created with SyckSec integration")
    return app, sycksec_client

def add_basic_routes(app, client):
    """Add basic routes demonstrating SyckSec usage"""
    
    @app.route('/')
    def index():
        return jsonify({
            'message': 'SyckSec Flask Example API',
            'version': '1.0.0-community',
            'endpoints': [
                '/auth/login',
                '/auth/token',
                '/protected',
                '/protected-decorator',
                '/batch',
                '/refresh'
            ]
        })
    
    @app.route('/auth/login', methods=['POST'])
    def login():
        """Simulate login and generate SyckSec token"""
        data = request.get_json()
        
        if not data or 'username' not in data:
            return jsonify({'error': 'Username required'}), 400
        
        username = data['username']
        
        # Simulate user authentication (in real app, verify password)
        if username in ['alice', 'bob', 'charlie']:
            try:
                # Generate token with optional device info
                device_info = data.get('device_info', {})
                ttl = data.get('ttl', 3600)  # Default 1 hour
                
                token = client.generate(
                    user_id=username,
                    ttl=ttl,
                    device_info=device_info
                )
                
                return jsonify({
                    'message': 'Login successful',
                    'token': token,
                    'token_type': 'SyckSec',
                    'expires_in': ttl,
                    'usage': f'Authorization: SyckSec {token}'
                })
                
            except Exception as e:
                return jsonify({'error': f'Token generation failed: {str(e)}'}), 500
        else:
            return jsonify({'error': 'Invalid credentials'}), 401
    
    @app.route('/auth/token', methods=['POST'])
    def verify_token():
        """Verify a SyckSec token"""
        data = request.get_json()
        
        if not data or 'token' not in data or 'user_id' not in data:
            return jsonify({'error': 'token and user_id required'}), 400
        
        try:
            payload = client.verify(data['token'], data['user_id'])
            return jsonify({
                'valid': True,
                'payload': payload,
                'time_remaining': payload['expires_at'] - int(time.time())
            })
        except TokenValidationError as e:
            return jsonify({
                'valid': False,
                'error': str(e)
            }), 401

def add_protected_routes(app, client):
    """Add protected routes requiring SyckSec tokens"""
    
    @app.route('/protected', methods=['GET', 'POST'])
    def protected_manual():
        """Manually protected route"""
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('SyckSec '):
            return jsonify({'error': 'SyckSec token required'}), 401
        
        token = auth_header[8:]  # Remove 'SyckSec ' prefix
        user_id = request.args.get('user_id') or (request.get_json() or {}).get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id parameter required'}), 400
        
        try:
            payload = client.verify(token, user_id)
            
            return jsonify({
                'message': 'Access granted to protected resource',
                'user_id': payload['user_id'],
                'token_info': {
                    'issued_at': payload['issued_at'],
                    'expires_at': payload['expires_at'],
                    'device_fingerprint': payload['device_fingerprint'],
                    'location': payload['location']
                },
                'request_info': {
                    'method': request.method,
                    'endpoint': request.endpoint,
                    'timestamp': int(time.time())
                }
            })
            
        except TokenValidationError as e:
            return jsonify({'error': f'Invalid token: {str(e)}'}), 401
    
    @app.route('/protected-decorator')
    @sycksec_required
    def protected_decorator():
        """Route protected with decorator"""
        return jsonify({
            'message': 'Access granted via decorator',
            'payload': g.sycksec_payload,
            'decoration': 'This route uses @sycksec_required decorator'
        })

def add_advanced_routes(app, client):
    """Add advanced routes showing batch operations and refresh"""
    
    @app.route('/batch/generate', methods=['POST'])
    def batch_generate():
        """Generate multiple tokens in batch"""
        data = request.get_json()
        
        if not data or 'requests' not in data:
            return jsonify({'error': 'requests array required'}), 400
        
        requests = data['requests']
        
        if len(requests) > 50:  # Community Edition limit
            return jsonify({'error': 'Community Edition: Maximum 50 tokens per batch'}), 400
        
        try:
            tokens = client.generate_batch(requests)
            
            results = []
            for i, token in enumerate(tokens):
                if token.startswith('ERROR:'):
                    results.append({
                        'index': i,
                        'status': 'error',
                        'error': token[7:]  # Remove 'ERROR: ' prefix
                    })
                else:
                    results.append({
                        'index': i,
                        'status': 'success',
                        'token': token
                    })
            
            return jsonify({
                'batch_size': len(requests),
                'results': results,
                'success_count': len([r for r in results if r['status'] == 'success']),
                'error_count': len([r for r in results if r['status'] == 'error'])
            })
            
        except Exception as e:
            return jsonify({'error': f'Batch generation failed: {str(e)}'}), 500
    
    @app.route('/batch/verify', methods=['POST'])
    def batch_verify():
        """Verify multiple tokens in batch"""
        data = request.get_json()
        
        if not data or 'requests' not in data:
            return jsonify({'error': 'requests array required'}), 400
        
        requests = data['requests']
        
        if len(requests) > 50:  # Community Edition limit
            return jsonify({'error': 'Community Edition: Maximum 50 tokens per batch'}), 400
        
        try:
            results = client.verify_batch(requests)
            
            valid_count = len([r for r in results if r['status'] == 'valid'])
            invalid_count = len([r for r in results if r['status'] == 'invalid'])
            
            return jsonify({
                'batch_size': len(requests),
                'results': results,
                'valid_count': valid_count,
                'invalid_count': invalid_count
            })
            
        except Exception as e:
            return jsonify({'error': f'Batch verification failed: {str(e)}'}), 500
    
    @app.route('/refresh', methods=['POST'])
    def refresh_token():
        """Refresh a token if needed"""
        data = request.get_json()
        
        if not data or 'token' not in data or 'user_id' not in data:
            return jsonify({'error': 'token and user_id required'}), 400
        
        threshold = data.get('threshold_seconds', 300)  # Default 5 minutes
        
        try:
            new_token = client.refresh(data['token'], data['user_id'], threshold)
            
            if new_token:
                return jsonify({
                    'refreshed': True,
                    'new_token': new_token,
                    'message': 'Token refreshed successfully'
                })
            else:
                return jsonify({
                    'refreshed': False,
                    'message': 'Token refresh not needed'
                })
                
        except Exception as e:
            return jsonify({'error': f'Refresh failed: {str(e)}'}), 400

def add_utility_routes(app, client):
    """Add utility routes for debugging and monitoring"""
    
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        try:
            # Test token generation/verification
            test_token = client.generate('health_check', ttl=60)
            test_payload = client.verify(test_token, 'health_check')
            
            return jsonify({
                'status': 'healthy',
                'sycksec': 'operational',
                'timestamp': int(time.time()),
                'test_token_valid': test_payload['user_id'] == 'health_check'
            })
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': int(time.time())
            }), 500
    
    @app.route('/stats')
    def get_stats():
        """Get basic statistics (if audit logging enabled)"""
        try:
            if hasattr(client.engine, 'audit_logger') and client.engine.audit_logger:
                stats = client.engine.audit_logger.get_stats()
                recent_events = client.engine.audit_logger.get_events(limit=10)
                
                return jsonify({
                    'statistics': stats,
                    'recent_events': recent_events,
                    'timestamp': int(time.time())
                })
            else:
                return jsonify({
                    'message': 'Audit logging not enabled',
                    'statistics': None
                })
        except Exception as e:
            return jsonify({'error': f'Stats retrieval failed: {str(e)}'}), 500

def demonstrate_flask_integration():
    """Run the Flask integration demonstration"""
    app, client = create_example_app()
    
    # Add all route groups
    add_basic_routes(app, client)
    add_protected_routes(app, client)
    add_advanced_routes(app, client)
    add_utility_routes(app, client)
    
    print("\n📚 Available Routes:")
    print("   GET  / - API information")
    print("   POST /auth/login - Generate token")
    print("   POST /auth/token - Verify token")
    print("   GET  /protected - Manual protection")
    print("   GET  /protected-decorator - Decorator protection")
    print("   POST /batch/generate - Batch token generation")
    print("   POST /batch/verify - Batch token verification")
    print("   POST /refresh - Token refresh")
    print("   GET  /health - Health check")
    print("   GET  /stats - Statistics (if audit enabled)")
    
    # Test the routes programmatically
    with app.test_client() as test_client:
        test_flask_routes(test_client, client)
    
    return app

def test_flask_routes(test_client, client):
    """Test the Flask routes programmatically"""
    print(f"\n🧪 Testing Flask Routes")
    print("=" * 28)
    
    # Test login
    login_response = test_client.post('/auth/login', 
        json={
            'username': 'alice',
            'ttl': 1800,
            'device_info': {
                'fingerprint': 'flask_test_device',
                'location': 'Test_Lab',
                'client_type': 'test_client'
            }
        },
        content_type='application/json'
    )
    
    print(f"✅ Login test: {login_response.status_code}")
    if login_response.status_code == 200:
        login_data = login_response.get_json()
        token = login_data['token']
        print(f"   Generated token: {token[:40]}...")
        
        # Test protected route
        protected_response = test_client.get('/protected?user_id=alice',
            headers={'Authorization': f'SyckSec {token}'}
        )
        print(f"✅ Protected route test: {protected_response.status_code}")
        
        # Test token verification
        verify_response = test_client.post('/auth/token',
            json={'token': token, 'user_id': 'alice'},
            content_type='application/json'
        )
        print(f"✅ Token verification test: {verify_response.status_code}")
        
        # Test batch generation
        batch_gen_response = test_client.post('/batch/generate',
            json={
                'requests': [
                    {'user_id': 'batch_user_1', 'ttl': 900},
                    {'user_id': 'batch_user_2', 'ttl': 900},
                    {'user_id': 'batch_user_3', 'ttl': 900}
                ]
            },
            content_type='application/json'
        )
        print(f"✅ Batch generation test: {batch_gen_response.status_code}")
        
        # Test health check
        health_response = test_client.get('/health')
        print(f"✅ Health check test: {health_response.status_code}")

def flask_deployment_example():
    """Show how to deploy Flask app with SyckSec"""
    print(f"\n🚀 Deployment Configuration")
    print("=" * 32)
    
    deployment_code = '''
# Production Flask app with SyckSec
from flask import Flask
from sycksec.integrations.flask_middleware import create_sycksec_app
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY')

# Initialize SyckSec with environment variable
sycksec = create_sycksec_app(
    app, 
    master_secret=os.environ.get('SYCKSEC_SECRET')
)

# Your routes here...

if __name__ == '__main__':
    # Development
    app.run(debug=True, host='0.0.0.0', port=5000)
    
# For production, use gunicorn:
# gunicorn --bind 0.0.0.0:5000 --workers 4 app:app
'''
    
    print("💡 Production Deployment Tips:")
    print("   1. Set SYCKSEC_SECRET environment variable")
    print("   2. Use gunicorn or uwsgi for production")
    print("   3. Enable HTTPS for token transmission")
    print("   4. Use Redis for shared audit logging")
    print("   5. Monitor token generation/verification rates")
    print("\n📄 Example production code:")
    print(deployment_code)

if __name__ == "__main__":
    try:
        app = demonstrate_flask_integration()
        flask_deployment_example()
        
        print("\n🎉 Flask integration examples completed!")
        print("\n💡 To run the Flask app:")
        print("   export SYCKSEC_SECRET='your-secret-key-here'")
        print("   python examples/flask_example.py")
        print("   # Then visit http://localhost:5000")
        
        # Uncomment to run the Flask development server
        # app.run(debug=True, host='0.0.0.0', port=5000)
        
    except Exception as e:
        print(f"❌ Flask example failed: {e}")
        import traceback
        traceback.print_exc()
