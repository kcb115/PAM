#!/usr/bin/env python3
"""
PAM API Testing Suite
Tests all backend endpoints for the PAM concert discovery app
"""

import requests
import sys
import json
from datetime import datetime
import uuid


class PAMAPITester:
    def __init__(self):
        self.base_url = "https://unknown-artists-near.preview.emergentagent.com/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_user_id = None
        self.test_results = []

    def log_result(self, test_name, status, message="", response_data=None):
        """Log test result"""
        self.tests_run += 1
        if status == "PASS":
            self.tests_passed += 1
            print(f"✅ {test_name}: {message}")
        else:
            print(f"❌ {test_name}: {message}")
        
        self.test_results.append({
            "test": test_name,
            "status": status,
            "message": message,
            "response_data": response_data
        })

    def test_health_check(self):
        """Test GET /api/ health check endpoint"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "PAM API is running" in data.get("message", ""):
                    self.log_result("Health Check", "PASS", f"Status: {response.status_code}, Message: {data.get('message')}")
                    return True
                else:
                    self.log_result("Health Check", "FAIL", f"Unexpected message: {data}")
                    return False
            else:
                self.log_result("Health Check", "FAIL", f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Health Check", "FAIL", f"Exception: {str(e)}")
            return False

    def test_create_user(self):
        """Test POST /api/users - Create user"""
        test_data = {
            "name": f"Test User {datetime.now().strftime('%H%M%S')}",
            "email": f"test_{datetime.now().strftime('%H%M%S')}@example.com",
            "concerts_per_month": 3,
            "ticket_budget": 75.0
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/users",
                json=test_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("id") and data.get("name") == test_data["name"] and data.get("email") == test_data["email"]:
                    self.test_user_id = data["id"]
                    self.log_result("Create User", "PASS", 
                                  f"User created successfully. ID: {self.test_user_id}, Name: {data['name']}, Email: {data['email']}")
                    return True
                else:
                    self.log_result("Create User", "FAIL", f"Invalid response data: {data}")
                    return False
            else:
                self.log_result("Create User", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("Create User", "FAIL", f"Exception: {str(e)}")
            return False

    def test_get_user(self):
        """Test GET /api/users/{user_id} - Get user by ID"""
        if not self.test_user_id:
            self.log_result("Get User", "SKIP", "No user ID available from create test")
            return False
            
        try:
            response = requests.get(f"{self.base_url}/users/{self.test_user_id}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("id") == self.test_user_id:
                    self.log_result("Get User", "PASS", 
                                  f"User retrieved successfully. Name: {data.get('name')}, Email: {data.get('email')}")
                    return True
                else:
                    self.log_result("Get User", "FAIL", f"User ID mismatch. Expected: {self.test_user_id}, Got: {data.get('id')}")
                    return False
            elif response.status_code == 404:
                self.log_result("Get User", "FAIL", "User not found (404)")
                return False
            else:
                self.log_result("Get User", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("Get User", "FAIL", f"Exception: {str(e)}")
            return False

    def test_update_user(self):
        """Test PUT /api/users/{user_id} - Update user"""
        if not self.test_user_id:
            self.log_result("Update User", "SKIP", "No user ID available")
            return False
            
        update_data = {
            "concerts_per_month": 5,
            "ticket_budget": 100.0,
            "city": "Austin, TX"
        }
        
        try:
            response = requests.put(
                f"{self.base_url}/users/{self.test_user_id}",
                json=update_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if (data.get("concerts_per_month") == 5 and 
                    data.get("ticket_budget") == 100.0 and 
                    data.get("city") == "Austin, TX"):
                    self.log_result("Update User", "PASS", 
                                  f"User updated successfully. Concerts/month: {data.get('concerts_per_month')}, Budget: ${data.get('ticket_budget')}, City: {data.get('city')}")
                    return True
                else:
                    self.log_result("Update User", "FAIL", f"Update data mismatch: {data}")
                    return False
            elif response.status_code == 404:
                self.log_result("Update User", "FAIL", "User not found (404)")
                return False
            else:
                self.log_result("Update User", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("Update User", "FAIL", f"Exception: {str(e)}")
            return False

    def test_spotify_login(self):
        """Test GET /api/spotify/login?user_id=xxx - Get Spotify OAuth URL"""
        if not self.test_user_id:
            self.log_result("Spotify Login", "SKIP", "No user ID available")
            return False
            
        try:
            response = requests.get(
                f"{self.base_url}/spotify/login",
                params={"user_id": self.test_user_id},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                auth_url = data.get("auth_url", "")
                if "accounts.spotify.com/authorize" in auth_url and "client_id=" in auth_url:
                    self.log_result("Spotify Login", "PASS", 
                                  f"Valid Spotify auth URL generated: {auth_url[:100]}...")
                    return True
                else:
                    self.log_result("Spotify Login", "FAIL", f"Invalid auth URL: {auth_url}")
                    return False
            else:
                self.log_result("Spotify Login", "FAIL", f"Status: {response.status_code}, Response: {response.text}")
                return False
        except Exception as e:
            self.log_result("Spotify Login", "FAIL", f"Exception: {str(e)}")
            return False

    def test_get_nonexistent_user(self):
        """Test GET /api/users/{invalid_id} - Should return 404"""
        fake_id = str(uuid.uuid4())
        try:
            response = requests.get(f"{self.base_url}/users/{fake_id}", timeout=10)
            
            if response.status_code == 404:
                self.log_result("Get Nonexistent User", "PASS", "Correctly returned 404 for invalid user ID")
                return True
            else:
                self.log_result("Get Nonexistent User", "FAIL", f"Expected 404, got {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Get Nonexistent User", "FAIL", f"Exception: {str(e)}")
            return False

    def test_invalid_user_creation(self):
        """Test POST /api/users with invalid data"""
        invalid_data = {
            "email": "invalid-email"  # Missing name, invalid email
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/users",
                json=invalid_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 422:  # FastAPI validation error
                self.log_result("Invalid User Creation", "PASS", "Correctly rejected invalid user data with 422")
                return True
            else:
                self.log_result("Invalid User Creation", "FAIL", f"Expected 422, got {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Invalid User Creation", "FAIL", f"Exception: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all tests"""
        print(f"🚀 Starting PAM API Tests")
        print(f"Testing endpoint: {self.base_url}")
        print("=" * 60)
        
        # Test order matters - create user first for other tests
        tests = [
            self.test_health_check,
            self.test_create_user,
            self.test_get_user,
            self.test_update_user,
            self.test_spotify_login,
            self.test_get_nonexistent_user,
            self.test_invalid_user_creation,
        ]
        
        for test in tests:
            test()
            
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️  Some tests failed")
            return False


def main():
    tester = PAMAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    with open("/tmp/backend_test_results.json", "w") as f:
        json.dump({
            "summary": {
                "total_tests": tester.tests_run,
                "passed_tests": tester.tests_passed,
                "success_rate": tester.tests_passed / tester.tests_run if tester.tests_run > 0 else 0,
                "timestamp": datetime.now().isoformat()
            },
            "test_results": tester.test_results,
            "test_user_id": tester.test_user_id
        }, f, indent=2)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())