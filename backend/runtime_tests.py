import httpx
import time
import os
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

def read_otp():
    time.sleep(1) # wait for file to be written
    try:
        with open("latest_otp.txt", "r") as f:
            return f.read().strip()
    except Exception as e:
        print(f"Failed to read OTP: {e}")
        return "123456"

def run_tests():
    print("Starting Runtime Tests...")
    results = {"passed": [], "failed": [], "skipped": []}
    
    def log_result(name, condition, error_msg=""):
        if condition:
            results["passed"].append(name)
            print(f"[PASS] {name} passed")
        else:
            results["failed"].append({"name": name, "error": error_msg})
            print(f"[FAIL] {name} failed: {error_msg}")

    client = httpx.Client(base_url=BASE_URL)
    
    test_email = f"test_{int(time.time())}@spip.com"
    test_password = "TestPassword@123"
    
    # 1. Register
    reg_res = client.post("/auth/register", json={
        "full_name": "Test User",
        "email": test_email,
        "password": test_password,
        "confirm_password": test_password,
        "role": "student",
        "terms_accepted": True
    })
    log_result("Register", reg_res.status_code == 201, reg_res.text)
    
    if reg_res.status_code != 201:
        print("Registration failed, aborting tests to avoid timeouts.")
        return
    
    # 2. Resend OTP
    resend_res = client.post("/auth/resend-otp", json={"email": test_email})
    log_result("Resend OTP", resend_res.status_code == 200, resend_res.text)
    
    # Read OTP
    otp = read_otp()
    
    # 3. Verify OTP
    verify_res = client.post("/auth/verify-otp", json={
        "email": test_email,
        "otp": otp
    })
    log_result("Verify OTP", verify_res.status_code == 200, verify_res.text)
    
    # 4. Login
    login_res = client.post("/auth/login", json={
        "email": test_email,
        "password": test_password
    })
    log_result("Login", login_res.status_code == 200, login_res.text)
    
    access_token = ""
    refresh_token = ""
    if login_res.status_code == 200:
        tokens = login_res.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        client.headers.update({"Authorization": f"Bearer {access_token}"})
    
    # 5. Profile Completion (GET /me, PUT /me)
    get_me = client.get("/users/me")
    log_result("Get Profile", get_me.status_code == 200, get_me.text)
    
    put_me = client.put("/users/me", json={
        "college": "Test College",
        "department": "Test Dept",
        "branch": "Test Branch",
        "semester": 5,
        "cgpa": 9.0,
        "skills": ["Python", "Testing"],
        "career_goal": "Tester"
    })
    log_result("Profile Update (Onboarding)", put_me.status_code == 200, put_me.text)
    
    # 6. Forgot Password
    forgot_res = client.post("/auth/forgot-password", json={"email": test_email})
    log_result("Forgot Password", forgot_res.status_code == 200, forgot_res.text)
    
    reset_otp = read_otp()
    
    # 7. Password Reset
    new_password = "NewPassword@123"
    reset_res = client.post("/auth/reset-password", json={
        "email": test_email,
        "otp": reset_otp,
        "new_password": new_password
    })
    log_result("Password Reset", reset_res.status_code == 200, reset_res.text)
    
    # 8. Login with new password
    client.headers.pop("Authorization", None)
    login2_res = client.post("/auth/login", json={
        "email": test_email,
        "password": new_password
    })
    log_result("Login after Reset", login2_res.status_code == 200, login2_res.text)
    
    if login2_res.status_code == 200:
        new_refresh = login2_res.json().get("refresh_token")
        
        # 9. Refresh Token
        refresh_res = client.post("/auth/refresh", headers={"x-refresh-token": new_refresh})
        log_result("Refresh Token", refresh_res.status_code == 200, refresh_res.text)
        
        if refresh_res.status_code == 200:
            # Update client token
            client.headers.update({"Authorization": f"Bearer {refresh_res.json().get('access_token')}"})
            
            # 10. Logout
            logout_res = client.post("/auth/logout", headers={"x-refresh-token": new_refresh})
            log_result("Logout", logout_res.status_code == 200, logout_res.text)
    
    # Generate Report
    report_content = f"""# Runtime Tests Report

## Passed ({len(results['passed'])})
"""
    for p in results["passed"]:
        report_content += f"- ✅ {p}\n"
        
    report_content += f"\n## Failed ({len(results['failed'])})\n"
    for f in results["failed"]:
        report_content += f"- ❌ {f['name']}: {f['error']}\n"
        
    with open("runtime_report.md", "w", encoding="utf-8") as f:
        f.write(report_content)
        
    print("\nSummary:")
    print(f"Passed: {len(results['passed'])}")
    print(f"Failed: {len(results['failed'])}")
    print("Report written to runtime_report.md")

if __name__ == "__main__":
    run_tests()
