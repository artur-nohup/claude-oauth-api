#!/usr/bin/env python3
"""
Claude OAuth API Test Client

This script demonstrates how to use the Claude OAuth API.
"""
import requests
import sys
import os
import time

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "your-secure-api-key-here")

def health_check():
    """Check API health"""
    try:
        response = requests.get(f"{API_BASE_URL}/")
        print(f"✅ Health check: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def get_status(headers):
    """Get current session status"""
    try:
        response = requests.get(f"{API_BASE_URL}/status", headers=headers)
        return response.json()
    except Exception as e:
        print(f"❌ Status check failed: {e}")
        return None

def login(email, verification_code=None):
    """Login to Claude"""
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    data = {"email": email}
    if verification_code:
        data["verification_code"] = verification_code
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/login",
            headers=headers,
            json=data,
            timeout=30
        )
        return response.json()
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return None

def authorize_oauth(oauth_url):
    """Process OAuth authorization"""
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    data = {"oauth_url": oauth_url}
    
    try:
        print("🔄 Processing OAuth authorization...")
        response = requests.post(
            f"{API_BASE_URL}/oauth/authorize",
            headers=headers,
            json=data,
            timeout=60
        )
        return response.json()
    except Exception as e:
        print(f"❌ OAuth authorization failed: {e}")
        return None

def interactive_login():
    """Interactive login flow"""
    print("\n🔐 Login to Claude")
    print("-" * 40)
    
    email = input("Enter your Claude email: ").strip()
    if not email:
        print("❌ Email is required!")
        return False
    
    # Step 1: Request verification code
    print("\n📧 Requesting verification code...")
    result = login(email)
    if not result:
        return False
    
    print(f"Response: {result['status']} - {result['message']}")
    
    if result.get("status") != "verification_required":
        print(f"❌ Unexpected response")
        return False
    
    # Step 2: Enter verification code
    code = input("\n📱 Enter the 6-digit verification code from your email: ").strip()
    if not code or len(code) != 6:
        print("❌ Invalid verification code!")
        return False
    
    print("\n🔄 Completing login...")
    result = login(email, code)
    if not result:
        return False
    
    print(f"Response: {result['status']} - {result['message']}")
    
    if result.get("status") == "success":
        print("✅ Login successful!")
        return True
    else:
        print(f"❌ Login failed")
        return False

def main():
    """Main test flow"""
    print("🤖 Claude OAuth API Test Client")
    print("=" * 50)
    print(f"API URL: {API_BASE_URL}")
    print(f"API Key: {'*' * (len(API_KEY) - 4) + API_KEY[-4:]}")
    
    # Health check
    if not health_check():
        print("❌ API is not responding. Please check if the service is running.")
        return
    
    headers = {"X-API-Key": API_KEY}
    
    while True:
        print("\n📋 Options:")
        print("1. Login to Claude")
        print("2. Check session status")
        print("3. Process OAuth URL")
        print("4. Exit")
        
        choice = input("\nSelect an option (1-4): ").strip()
        
        if choice == "1":
            interactive_login()
        
        elif choice == "2":
            status = get_status(headers)
            if status:
                print(f"\n📊 Session Status:")
                print(f"  Browser active: {status.get('browser_active')}")
                print(f"  Pages open: {status.get('pages_open')}")
                print(f"  Current URL: {status.get('current_url')}")
                print(f"  Logged in: {status.get('logged_in')}")
        
        elif choice == "3":
            # Check if logged in first
            status = get_status(headers)
            if not status or not status.get("logged_in"):
                print("❌ Not logged in! Please login first (option 1)")
                continue
            
            oauth_url = input("\n🔗 Enter the Claude OAuth URL: ").strip()
            if not oauth_url:
                print("❌ No URL provided!")
                continue
            
            result = authorize_oauth(oauth_url)
            if result:
                if result.get("success"):
                    print(f"\n✅ Success!")
                    print(f"  Authorization code: {result.get('code')}")
                    print(f"  Request ID: {result.get('request_id')}")
                    print(f"  Timestamp: {result.get('timestamp')}")
                else:
                    print(f"\n❌ Failed: {result.get('error')}")
        
        elif choice == "4":
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid option!")

if __name__ == "__main__":
    # Allow API URL to be passed as command line argument
    if len(sys.argv) > 1:
        API_BASE_URL = sys.argv[1]
    
    main()
