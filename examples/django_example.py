#!/usr/bin/env python3
"""
Django integration example for SyckSec Community Edition
Demonstrates how to integrate SyckSec with Django applications
"""

import os
import sys
import django
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.test import RequestFactory

# Configure Django settings for this example
if not settings.configured:
    settings.configure(
        DEBUG=True,
        SECRET_KEY='django-example-secret-key-for-testing',
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
        ],
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        MIDDLEWARE=[
            'django.middleware.common.CommonMiddleware',
            'django.contrib.auth.middleware.AuthenticationMiddleware',
        ],
        AUTHENTICATION_BACKENDS=[
            'sycksec.integrations.django_auth.SyckSecAuthenticationBackend',
            'django.contrib.auth.backends.ModelBackend',
        ]
    )
    
    django.setup()

from django.core.management import execute_from_command_line
from sycksec import create_client
from sycksec.integrations.django_auth import SyckSecAuthenticationBackend, SyckSecMiddleware

def setup_django_example():
    """Set up Django example environment"""
    print("🐍 SyckSec + Django Integration Example")
    print("=" * 45)
    
    # Create database tables
    from django.core.management import call_command
    call_command('migrate', verbosity=0, interactive=False)
    
    # Create a test user
    user, created = User.objects.get_or_create(
        username='django_user',
        defaults={
            'email': 'django@example.com',
            'first_name': 'Django',
            'last_name': 'User'
        }
    )
    
    if created:
        user.set_password('testpassword')
        user.save()
        print(f"✅ Created test user: {user.username} (ID: {user.id})")
    else:
        print(f"ℹ️  Using existing user: {user.username} (ID: {user.id})")
    
    return user

def django_authentication_example(user):
    """Demonstrate SyckSec authentication backend"""
    print(f"\n🔐 Authentication Backend Example")
    print("=" * 35)
    
    # Generate a token for the user
    client = create_client("django-sycksec-secret-32-chars!!")
    token = client.generate(str(user.id), ttl=3600)
    
    print(f"✅ Generated token for user {user.username}:")
    print(f"   Token: {token[:50]}...")
    
    # Use the authentication backend
    auth_backend = SyckSecAuthenticationBackend()
    
    # Create a mock request
    factory = RequestFactory()
    request = factory.get('/test/')
    request.user = user
    
    # Authenticate with token
    authenticated_user = auth_backend.authenticate(
        request, 
        token=token, 
        user_id=str(user.id)
    )
    
    if authenticated_user:
        print(f"✅ Authentication successful:")
        print(f"   Username: {authenticated_user.username}")
        print(f"   Email: {authenticated_user.email}")
        print(f"   User ID: {authenticated_user.id}")
    else:
        print("❌ Authentication failed")
    
    # Test with invalid token
    invalid_auth = auth_backend.authenticate(
        request,
        token="invalid-token",
        user_id=str(user.id)
    )
    
    if not invalid_auth:
        print("✅ Invalid token correctly rejected")

def django_middleware_example(user):
    """Demonstrate SyckSec middleware"""
    print(f"\n🔧 Middleware Integration Example")
    print("=" * 38)
    
    client = create_client("django-middleware-secret-32!!")
    token = client.generate(str(user.id), ttl=1800)
    
    # Create middleware instance
    def get_response(request):
        return JsonResponse({
            'message': 'Protected endpoint accessed',
            'user': request.user.username,
            'sycksec_payload': getattr(request, 'sycksec_payload', None)
        })
    
    middleware = SyckSecMiddleware(get_response)
    
    # Create request with SyckSec token
    factory = RequestFactory()
    request = factory.get('/protected/', HTTP_AUTHORIZATION=f'SyckSec {token}')
    request.user = user
    
    # Process request through middleware
    response = middleware(request)
    
    print(f"✅ Request processed through middleware:")
    if hasattr(request, 'sycksec_payload'):
        print(f"   SyckSec payload attached: {request.sycksec_payload['user_id']}")
        print(f"   Token expires at: {request.sycksec_payload['expires_at']}")
    else:
        print("   No SyckSec payload (token validation failed)")

def django_views_example(user):
    """Example Django views using SyckSec"""
    print(f"\n📄 Django Views Example")
    print("=" * 28)
    
    from django.views.decorators.csrf import csrf_exempt
    from django.utils.decorators import method_decorator
    from django.views import View
    import json
    
    client = create_client("django-views-secret-32-chars!")
    
    # Function-based view
    def sycksec_protected_view(request):
        """Protected view that requires SyckSec token"""
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('SyckSec '):
            return JsonResponse({'error': 'SyckSec token required'}, status=401)
        
        token = auth_header[8:]  # Remove 'SyckSec ' prefix
        user_id = request.GET.get('user_id') or request.POST.get('user_id')
        
        if not user_id:
            return JsonResponse({'error': 'user_id parameter required'}, status=400)
        
        try:
            payload = client.verify(token, user_id)
            return JsonResponse({
                'message': 'Access granted',
                'user_id': payload['user_id'],
                'device': payload['device_fingerprint'],
                'expires_at': payload['expires_at']
            })
        except Exception as e:
            return JsonResponse({'error': f'Invalid token: {str(e)}'}, status=401)
    
    # Class-based view
    @method_decorator(csrf_exempt, name='dispatch')
    class SyckSecAPIView(View):
        def get(self, request):
            return JsonResponse({'message': 'GET endpoint', 'method': 'GET'})
        
        def post(self, request):
            # Parse JSON body
            try:
                data = json.loads(request.body)
                token = data.get('token')
                user_id = data.get('user_id')
                
                if not token or not user_id:
                    return JsonResponse({'error': 'token and user_id required'}, status=400)
                
                payload = client.verify(token, user_id)
                return JsonResponse({
                    'message': 'POST endpoint access granted',
                    'user_id': payload['user_id'],
                    'method': 'POST',
                    'data_received': data
                })
                
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
            except Exception as e:
                return JsonResponse({'error': f'Token error: {str(e)}'}, status=401)
    
    # Test the views
    factory = RequestFactory()
    token = client.generate(str(user.id), ttl=1800)
    
    # Test function-based view
    request = factory.get(
        f'/protected/?user_id={user.id}',
        HTTP_AUTHORIZATION=f'SyckSec {token}'
    )
    
    response = sycksec_protected_view(request)
    print(f"✅ Function-based view response: {response.status_code}")
    
    # Test class-based view POST
    api_view = SyckSecAPIView()
    post_data = json.dumps({
        'token': token,
        'user_id': str(user.id),
        'message': 'Hello from client'
    })
    
    request = factory.post(
        '/api/',
        data=post_data,
        content_type='application/json'
    )
    
    response = api_view.post(request)
    print(f"✅ Class-based view response: {response.status_code}")

def django_admin_integration():
    """Example of SyckSec with Django Admin"""
    print(f"\n👑 Django Admin Integration")
    print("=" * 32)
    
    from django.contrib import admin
    from django.contrib.auth.admin import UserAdmin
    from django.contrib.auth.models import User
    
    # Custom admin action using SyckSec
    def generate_sycksec_tokens(modeladmin, request, queryset):
        """Admin action to generate SyckSec tokens for selected users"""
        client = create_client("admin-action-secret-32-chars!")
        results = []
        
        for user in queryset:
            try:
                token = client.generate(str(user.id), ttl=7200)  # 2 hours
                results.append(f"✅ {user.username}: {token[:30]}...")
            except Exception as e:
                results.append(f"❌ {user.username}: Error - {str(e)}")
        
        return results
    
    generate_sycksec_tokens.short_description = "Generate SyckSec tokens for selected users"
    
    # Example of how you'd add this to admin
    print("✅ Admin integration example:")
    print("   - Custom admin action for token generation")
    print("   - Can be added to UserAdmin.actions")
    print("   - Allows bulk token generation from admin interface")
    
    # Simulate running the admin action
    users = User.objects.all()[:2]  # Get first 2 users
    results = generate_sycksec_tokens(None, None, users)
    
    print("\n📊 Admin Action Results:")
    for result in results:
        print(f"   {result}")

if __name__ == "__main__":
    try:
        # Setup
        user = setup_django_example()
        
        # Run examples
        django_authentication_example(user)
        django_middleware_example(user)
        django_views_example(user)
        django_admin_integration()
        
        print("\n🎉 Django integration examples completed!")
        print("\n💡 Integration Tips:")
        print("   1. Add SyckSecAuthenticationBackend to AUTHENTICATION_BACKENDS")
        print("   2. Use SyckSecMiddleware for automatic token processing")
        print("   3. Set Authorization header: 'SyckSec <token>'")
        print("   4. Always validate user_id matches token")
        print("   5. Handle TokenValidationError exceptions properly")
        
    except Exception as e:
        print(f"❌ Example failed: {e}")
        import traceback
        traceback.print_exc()
