#!/usr/bin/env python3
"""API Testing Script"""

import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_api():
    print("="*50)
    print("Amazon Insights Platform - API Testing")
    print("="*50)
    
    # 1. Register a new user
    print("\n1. Registering new user...")
    register_data = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "Test1234!",
        "full_name": "Test User"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
    if response.status_code == 200:
        user = response.json()
        print(f"✅ User created: {user['username']} (ID: {user['id']})")
    else:
        print(f"❌ Registration failed: {response.text}")
        
    # 2. Login to get token
    print("\n2. Logging in...")
    login_data = {
        "username": "testuser",  # Use username, not email
        "password": "Test1234!"
    }
    
    response = requests.post(
        f"{BASE_URL}/auth/token",  # Changed from /login to /token
        data=login_data,  # Note: form data, not JSON
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    if response.status_code == 200:
        token_data = response.json()
        access_token = token_data["access_token"]
        print(f"✅ Login successful! Token: {access_token[:20]}...")
        
        # Set auth header
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # 3. Test product endpoints
        print("\n3. Testing Product Endpoints...")
        
        # Create a product
        print("\n   a. Creating a product...")
        product_data = {
            "asin": "B08N5WRWNW",  # Echo Dot ASIN
            "title": "Echo Dot (4th Gen)",
            "category": "Smart Home"
        }
        
        response = requests.post(
            f"{BASE_URL}/products/",
            json=product_data,
            headers=headers
        )
        
        if response.status_code == 200:
            product = response.json()
            print(f"   ✅ Product created: {product['title']} (ID: {product['id']})")
            product_id = product['id']
            
            # List products
            print("\n   b. Listing products...")
            response = requests.get(f"{BASE_URL}/products/", headers=headers)
            if response.status_code == 200:
                products = response.json()
                print(f"   ✅ Found {len(products)} product(s)")
                for p in products:
                    print(f"      - {p['asin']}: {p['title']}")
            
            # Get single product
            print(f"\n   c. Getting product {product_id}...")
            response = requests.get(f"{BASE_URL}/products/{product_id}", headers=headers)
            if response.status_code == 200:
                product = response.json()
                print(f"   ✅ Product details:")
                print(f"      - ASIN: {product['asin']}")
                print(f"      - Title: {product['title']}")
                print(f"      - Active: {product['is_active']}")
                
            # Test batch import
            print("\n   d. Testing batch import...")
            batch_data = {
                "asins": ["B09B8V1LZ3", "B09B93ZDG4", "B08H75RTZ8"],  # More Echo products
                "default_category": "Smart Home"
            }
            
            response = requests.post(
                f"{BASE_URL}/products/batch-import",
                json=batch_data,
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ Batch import complete:")
                print(f"      - Imported: {result['total_imported']} products")
                print(f"      - Skipped: {result['total_skipped']} products")
                
        else:
            print(f"   ❌ Product creation failed: {response.text}")
            
    else:
        print(f"❌ Login failed: {response.text}")
    
    print("\n" + "="*50)
    print("Testing complete!")
    print("="*50)
    print("\n📌 You can now access:")
    print("   - API Docs: http://localhost:8000/api/v1/docs")
    print("   - Flower: http://localhost:5555")
    print("\nUse the token above to authenticate in the Swagger UI!")

if __name__ == "__main__":
    test_api()