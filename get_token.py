#!/usr/bin/env python3
"""Get JWT Token for API Testing"""

import requests
import json

def get_token():
    # Login credentials
    login_data = {
        "username": "testuser",
        "password": "Test1234!"
    }
    
    # Get token
    response = requests.post(
        "http://localhost:8000/api/v1/auth/token",
        data=login_data,  # Note: form data, not JSON
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code == 200:
        token_data = response.json()
        token = token_data["access_token"]
        
        print("✅ Login successful!")
        print("\n" + "="*60)
        print("Your JWT Token:")
        print("="*60)
        print(token)
        print("="*60)
        
        print("\n📋 How to use this token:")
        print("\n1. In Swagger UI:")
        print("   - Click 'Authorize' button")
        print("   - Enter: Bearer " + token[:20] + "...")
        print("   - Click 'Authorize'")
        
        print("\n2. With curl:")
        print(f'   curl -H "Authorization: Bearer {token[:20]}..." \\')
        print('        http://localhost:8000/api/v1/products/')
        
        print("\n3. In Postman:")
        print("   - Go to Headers tab")
        print("   - Add: Authorization = Bearer [token]")
        
        return token
    else:
        print(f"❌ Login failed: {response.text}")
        return None

if __name__ == "__main__":
    get_token()