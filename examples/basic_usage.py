#!/usr/bin/env python3
"""
Basic usage examples for SyckSec Community Edition
Demonstrates core token generation and verification functionality
"""

import os
import time
from sycksec import create_client, SyckSec, SyckSecConfig

def basic_example():
    """Basic token generation and verification"""
    print("🔐 SyckSec Community Edition - Basic Usage")
    print("=" * 50)
    
    # Method 1: Quick setup with create_client
    client = create_client("my-super-secret-32-character-key!!")
    
    # Generate a token for user
    user_id = "john_doe_123"
    token = client.generate(user_id, ttl=3600)  # 1 hour expiry
    
    print(f"✅ Generated token for {user_id}:")
    print(f"   {token}")
    print(f"   Length: {len(token)} characters")
    
    # Verify the token
    payload = client.verify(token, user_id)
    print(f"\n✅ Token verified successfully:")
    print(f"   User ID: {payload['user_id']}")
    print(f"   Issued at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(payload['issued_at']))}")
    print(f"   Expires at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(payload['expires_at']))}")
    print(f"   Device fingerprint: {payload['device_fingerprint']}")

def advanced_configuration():
    """Advanced configuration example"""
    print("\n🔧 Advanced Configuration")
    print("=" * 30)
    
    # Method 2: Custom configuration
    config = SyckSecConfig(
        master_secret="advanced-secret-key-32-chars-long!",
        default_ttl=1800,  # 30 minutes
        max_ttl=7200,      # 2 hours max
        enable_audit_logging=True,
        debug=True
    )
    
    client = SyckSec(config)
    
    # Generate token with device context
    device_info = {
        "fingerprint": "mobile_device_abc123",
        "location": "US_West",
        "pattern": "mobile_app",
        "client_type": "ios"
    }
    
    token = client.generate(
        user_id="jane_smith_456",
        ttl=2700,  # 45 minutes
        device_info=device_info
    )
    
    print(f"✅ Generated context-aware token:")
    print(f"   {token[:50]}...")
    
    # Verify with context
    payload = client.verify(token, "jane_smith_456")
    print(f"\n✅ Context-aware verification:")
    print(f"   Location: {payload['location']}")
    print(f"   Device type: {payload['client_type']}")
    print(f"   Usage pattern: {payload['usage_pattern']}")

def batch_operations():
    """Batch token operations example"""
    print("\n📦 Batch Operations (Community: max 50)")
    print("=" * 40)
    
    client = create_client("batch-secret-key-32-characters-long!")
    
    # Batch generation
    requests = [
        {"user_id": f"user_{i}", "ttl": 900}
        for i in range(1, 6)  # Generate 5 tokens
    ]
    
    tokens = client.generate_batch(requests)
    print(f"✅ Generated {len(tokens)} tokens in batch:")
    for i, token in enumerate(tokens, 1):
        if not token.startswith("ERROR"):
            print(f"   User {i}: {token[:30]}...")
        else:
            print(f"   User {i}: {token}")
    
    # Batch verification
    verification_requests = [
        {"token": token, "user_id": f"user_{i}"}
        for i, token in enumerate(tokens, 1)
        if not token.startswith("ERROR")
    ]
    
    results = client.verify_batch(verification_requests)
    print(f"\n✅ Verified {len(results)} tokens in batch:")
    for i, result in enumerate(results, 1):
        if result["status"] == "valid":
            print(f"   User {i}: Valid (expires: {time.strftime('%H:%M:%S', time.localtime(result['data']['expires_at']))})")
        else:
            print(f"   User {i}: Invalid - {result['error']}")

def token_refresh_example():
    """Token auto-refresh example"""
    print("\n🔄 Token Auto-Refresh")
    print("=" * 25)
    
    client = create_client("refresh-secret-key-32-characters!!")
    
    # Generate a short-lived token
    user_id = "refresh_user_789"
    token = client.generate(user_id, ttl=600)  # 10 minutes
    
    print(f"✅ Generated short-lived token (10min TTL)")
    payload = client.verify(token, user_id)
    time_left = payload['expires_at'] - int(time.time())
    print(f"   Time remaining: {time_left} seconds")
    
    # Check if refresh is needed (threshold: 15 minutes)
    new_token = client.refresh(token, user_id, threshold_seconds=900)
    
    if new_token:
        print(f"✅ Token refreshed automatically:")
        print(f"   Old: {token[:30]}...")
        print(f"   New: {new_token[:30]}...")
        
        # Verify new token
        new_payload = client.verify(new_token, user_id)
        new_time_left = new_payload['expires_at'] - int(time.time())
        print(f"   New expiry: {new_time_left} seconds from now")
    else:
        print("ℹ️  No refresh needed (token not expiring soon)")

def error_handling_example():
    """Error handling examples"""
    print("\n⚠️  Error Handling")
    print("=" * 20)
    
    from sycksec.utils.exceptions import TokenGenerationError, TokenValidationError
    
    client = create_client("error-handling-secret-32-chars!!")
    
    # Invalid user ID
    try:
        client.generate("", ttl=900)
    except TokenGenerationError as e:
        print(f"✅ Caught generation error: {e}")
    
    # Invalid token verification
    try:
        client.verify("invalid-token-format", "some_user")
    except TokenValidationError as e:
        print(f"✅ Caught validation error: {e}")
    
    # Wrong user verification
    valid_token = client.generate("correct_user")
    try:
        client.verify(valid_token, "wrong_user")
    except TokenValidationError as e:
        print(f"✅ Caught user mismatch: {e}")

def audit_logging_example():
    """Audit logging demonstration"""
    print("\n📋 Audit Logging")
    print("=" * 18)
    
    config = SyckSecConfig(
        master_secret="audit-secret-key-32-characters-!",
        enable_audit_logging=True
    )
    client = SyckSec(config)
    
    # Perform some operations
    user1_token = client.generate("audit_user_1")
    user2_token = client.generate("audit_user_2") 
    
    client.verify(user1_token, "audit_user_1")
    client.verify(user2_token, "audit_user_2")
    
    # Try invalid verification
    try:
        client.verify("invalid_token", "audit_user_1")
    except:
        pass
    
    # Get audit statistics
    if client.engine.audit_logger:
        stats = client.engine.audit_logger.get_stats()
        print(f"✅ Audit Statistics:")
        print(f"   Total events: {stats['total_events']}")
        print(f"   Event types: {', '.join(stats['event_types'])}")
        print(f"   Unique users: {stats['unique_users']}")
        
        # Get recent events
        recent_events = client.engine.audit_logger.get_events(limit=3)
        print(f"\n📝 Recent Events:")
        for event in recent_events[-3:]:
            print(f"   {event['timestamp'][:19]} - {event['event_type']} - {event['user_id']}")

if __name__ == "__main__":
    # Run all examples
    basic_example()
    advanced_configuration()
    batch_operations()
    token_refresh_example()
    error_handling_example()
    audit_logging_example()
    
    print("\n🎉 All examples completed successfully!")
    print("\n💡 Next steps:")
    print("   - Try the Django example: python examples/django_example.py")
    print("   - Try the Flask example: python examples/flask_example.py")
    print("   - Check out the Node.js example: node examples/node_example.js")
    print("   - Explore enterprise features: https://sycksec.com/enterprise")
