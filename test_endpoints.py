#!/usr/bin/env python3
"""
Quick test script to verify ticket creation endpoint works
"""
import requests
import json

BASE_URL = "http://localhost:8003"

def test_ticket_creation():
    """Test both Jira and ServiceNow ticket creation"""
    
    test_cases = [
        {
            "type": "jira",
            "risk_id": "test-risk-001",
            "title": "Test Security Risk",
            "description": "This is a test security risk for demo purposes"
        },
        {
            "type": "servicenow", 
            "risk_id": "test-risk-002",
            "title": "Another Test Risk",
            "description": "ServiceNow test ticket"
        }
    ]
    
    for test_case in test_cases:
        print(f"\n--- Testing {test_case['type'].upper()} ticket creation ---")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/tickets",
                json=test_case,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success!")
                print(f"   Ticket ID: {result.get('id')}")
                print(f"   Demo Message: {result.get('demo_message')}")
                print(f"   URL: {result.get('url', 'None (demo mode)')}")
            else:
                print(f"❌ Failed: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print(f"❌ Could not connect to backend at {BASE_URL}")
            print("   Make sure the backend is running on port 8003")
        except Exception as e:
            print(f"❌ Error: {e}")

def test_mute_endpoint():
    """Test the mute endpoint"""
    print(f"\n--- Testing MUTE endpoint ---")
    
    test_mute = {
        "id": "test-risk-001",
        "days": 7,
        "reason": "Testing mute functionality"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/mutes",
            json=test_mute,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success!")
            print(f"   Muted until: {result.get('until')}")
            print(f"   Reason: {result.get('reason')}")
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to backend at {BASE_URL}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🧪 Testing Censys Summarization Agent Endpoints")
    print("=" * 50)
    
    # Test health endpoint first
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        if response.status_code == 200:
            print("✅ Backend is running!")
            print(f"   Health check: {response.json()}")
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to backend at {BASE_URL}")
        print("   Please start the backend first with: ./run_backend.ps1 -Port 8003")
        exit(1)
    
    test_ticket_creation()
    test_mute_endpoint()
    
    print("\n🎉 Test completed!")