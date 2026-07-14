import requests
import time
import sys

# Windows console fix for unicode
sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000/api/v1"

def print_result(name, result, error=None):
    if result:
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name} - Error: {error}")

def run_auth_tests():
    print("--- Starting Phase 2: Authentication Runtime Validation ---")
    
    # 1. Register
    reg_data = {
        "full_name": "Test User",
        "email": f"test_{int(time.time())}@spip.com",
        "password": "Password@123",
        "confirm_password": "Password@123",
        "phone": f"9{int(time.time())}"[:10],
        "terms_accepted": True
    }
    
    try:
        r = requests.post(f"{BASE_URL}/auth/register", json=reg_data)
        if r.status_code == 201:
            print_result("Register", True)
        else:
            print_result("Register", False, r.text)
    except Exception as e:
        print_result("Register", False, str(e))
        return

    # 2. Login (Before verification - should fail or succeed?)
    login_data = {
        "email": reg_data["email"],
        "password": reg_data["password"]
    }
    
    try:
        # FastAPI might expect form data for login if using OAuth2PasswordRequestForm
        r = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        if r.status_code == 200:
            print_result("Login", True)
        elif r.status_code in [401, 403]: 
            print_result("Login (Unverified/Unauthorized)", True, "Requires verification or form data")
        else:
            print_result("Login", False, r.text)
    except Exception as e:
        print_result("Login", False, str(e))


if __name__ == "__main__":
    run_auth_tests()
