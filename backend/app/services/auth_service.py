from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.domain.users.models import User, UserRole, UserSession, VerificationToken, TokenType, EmailOTP, AuditLog
from app.domain.users.schemas import UserCreate, UserLogin
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings
from datetime import datetime, timedelta, timezone
import secrets
import random

class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def _log_audit(self, user_id: int, action: str, status_msg: str, ip_address: str = None, user_agent: str = None, details: str = None):
        log = AuditLog(
            user_id=user_id,
            action=action,
            status=status_msg,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        self.db.add(log)
        self.db.commit()

    def register_user(self, user_in: UserCreate, ip_address: str = None, user_agent: str = None) -> User:
        if self.db.query(User).filter(User.email == user_in.email).first():
            self._log_audit(None, "Registration", "Failed - Duplicate Email", ip_address, user_agent, f"Email: {user_in.email}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        
        if user_in.phone and self.db.query(User).filter(User.phone == user_in.phone).first():
            self._log_audit(None, "Registration", "Failed - Duplicate Phone", ip_address, user_agent, f"Phone: {user_in.phone}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number already registered")

        db_user = User(
            email=user_in.email,
            password_hash=get_password_hash(user_in.password),
            full_name=user_in.full_name,
            phone=user_in.phone,
            role=user_in.role,
            college=user_in.college,
            department=user_in.department,
            branch=user_in.branch,
            semester=user_in.semester,
            cgpa=user_in.cgpa,
            skills=user_in.skills or [],
            career_goal=user_in.career_goal,
            resume_url=user_in.resume_url,
            profile_picture=user_in.profile_picture,
            linkedin_url=user_in.linkedin_url,
            github_url=user_in.github_url,
            portfolio_url=user_in.portfolio_url,
            roll_number=user_in.roll_number,
            employee_id=user_in.employee_id,
            is_active=True,
            is_verified=False
        )
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        self._log_audit(db_user.id, "Registration", "Success", ip_address, user_agent)
        
        self.generate_and_send_otp(db_user, TokenType.EMAIL_VERIFICATION)
        return db_user

    def generate_and_send_otp(self, user: User, purpose: TokenType):
        # Generate 6-digit OTP
        otp_plain = f"{random.randint(100000, 999999)}"
        otp_hash = get_password_hash(otp_plain)

        # Invalidate previous OTPs for this purpose
        self.db.query(EmailOTP).filter(
            EmailOTP.user_id == user.id,
            EmailOTP.purpose == purpose,
            EmailOTP.is_used == False
        ).update({"is_used": True})

        otp_record = EmailOTP(
            user_id=user.id,
            otp_hash=otp_hash,
            purpose=purpose,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            attempts=0
        )
        self.db.add(otp_record)
        self.db.commit()

        # TODO: Send email via Brevo or fallback
        print(f"--- MOCK EMAIL --- To: {user.email} | OTP: {otp_plain} | Purpose: {purpose}")
        with open("latest_otp.txt", "w") as f:
            f.write(otp_plain)

    def resend_otp(self, email: str, purpose: TokenType, ip_address: str = None, user_agent: str = None):
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=400, detail="User not found")
        
        # Check rate limits for resending (e.g. max 5 active otps generated today) - skipped for brevity but would be added here
        self.generate_and_send_otp(user, purpose)
        self._log_audit(user.id, "OTP Resend", "Success", ip_address, user_agent, f"Purpose: {purpose}")
        return {"message": "OTP sent successfully"}

    def verify_otp(self, email: str, otp: str, purpose: TokenType, ip_address: str = None, user_agent: str = None):
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=400, detail="Invalid request")

        otp_record = self.db.query(EmailOTP).filter(
            EmailOTP.user_id == user.id,
            EmailOTP.purpose == purpose,
            EmailOTP.is_used == False
        ).order_by(EmailOTP.created_at.desc()).first()

        if not otp_record:
            self._log_audit(user.id, "OTP Verification", "Failed - No active OTP", ip_address, user_agent)
            raise HTTPException(status_code=400, detail="No active OTP found. Please request a new one.")

        if otp_record.expires_at < datetime.now(timezone.utc):
            self._log_audit(user.id, "OTP Verification", "Failed - Expired", ip_address, user_agent)
            raise HTTPException(status_code=400, detail="OTP has expired")

        otp_record.attempts += 1
        self.db.commit()

        if otp_record.attempts > 5:
            otp_record.is_used = True
            self.db.commit()
            self._log_audit(user.id, "OTP Verification", "Failed - Max attempts", ip_address, user_agent)
            raise HTTPException(status_code=400, detail="Maximum attempts reached. Request a new OTP.")

        if not verify_password(otp, otp_record.otp_hash):
            self._log_audit(user.id, "OTP Verification", "Failed - Invalid OTP", ip_address, user_agent)
            raise HTTPException(status_code=400, detail="Invalid OTP")

        # Success
        otp_record.is_used = True
        if purpose == TokenType.EMAIL_VERIFICATION:
            user.is_verified = True
            
        self.db.commit()
        self._log_audit(user.id, "OTP Verification", "Success", ip_address, user_agent, f"Purpose: {purpose}")
        return {"message": "Verification successful"}

    def login(self, login_data: UserLogin, ip_address: str, device_info: str):
        # 1. User Exists
        user = self.db.query(User).filter(User.email == login_data.email).first()
        if not user:
            self._log_audit(None, "Login", "Failed - User Not Found", ip_address, device_info, f"Email: {login_data.email}")
            raise HTTPException(status_code=401, detail="Incorrect email or password")
            
        # 2. Account Active
        if not user.is_active:
            self._log_audit(user.id, "Login", "Failed - Inactive Account", ip_address, device_info)
            raise HTTPException(status_code=403, detail="Account is disabled")

        # 3. Email Verified
        if not user.is_verified:
            self._log_audit(user.id, "Login", "Failed - Unverified Email", ip_address, device_info)
            raise HTTPException(status_code=403, detail="Please verify your email first")

        # 4. Account Locked
        if user.is_locked:
            self._log_audit(user.id, "Login", "Failed - Account Locked", ip_address, device_info)
            raise HTTPException(status_code=403, detail="Account is locked due to too many failed attempts")

        # 5. Password Verification
        if not verify_password(login_data.password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.is_locked = True
                self._log_audit(user.id, "Account Lockout", "Locked out after 5 failed attempts", ip_address, device_info)
            self.db.commit()
            self._log_audit(user.id, "Login", "Failed - Incorrect Password", ip_address, device_info)
            raise HTTPException(status_code=401, detail="Incorrect email or password")

        # Reset failed attempts
        user.failed_login_attempts = 0
        
        # 6 & 7. Generate Tokens
        access_token = create_access_token(subject=str(user.id))
        refresh_token_str = secrets.token_urlsafe(64)
        expires_days = 30 if login_data.remember_me else settings.REFRESH_TOKEN_EXPIRE_DAYS
        
        # Parse basic browser/os from device_info (User-Agent) for UserSession
        browser = "Unknown"
        os = "Unknown"
        if device_info:
            if "Chrome" in device_info: browser = "Chrome"
            elif "Firefox" in device_info: browser = "Firefox"
            elif "Safari" in device_info: browser = "Safari"
            
            if "Windows" in device_info: os = "Windows"
            elif "Mac" in device_info: os = "MacOS"
            elif "Linux" in device_info: os = "Linux"
            elif "Android" in device_info: os = "Android"
            elif "iPhone" in device_info: os = "iOS"

        session = UserSession(
            user_id=user.id,
            refresh_token=refresh_token_str,
            device_info=device_info,
            browser=browser,
            os=os,
            ip_address=ip_address,
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_days)
        )
        self.db.add(session)
        
        # 8. Update Last Login
        user.last_login = datetime.now(timezone.utc)
        self.db.commit()

        # 9. Create Audit Log
        self._log_audit(user.id, "Login", "Success", ip_address, device_info)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token_str,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }

    def refresh_token(self, refresh_token: str, ip_address: str, user_agent: str = None):
        session = self.db.query(UserSession).filter(UserSession.refresh_token == refresh_token).first()
        if not session or session.is_revoked or session.expires_at < datetime.now(timezone.utc):
            if session:
                self._log_audit(session.user_id, "Refresh Token", "Failed - Invalid/Expired", ip_address, user_agent)
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

        session.is_revoked = True
        
        user = session.user
        if not user.is_active or user.is_locked:
             self._log_audit(user.id, "Refresh Token", "Failed - Account Inactive/Locked", ip_address, user_agent)
             raise HTTPException(status_code=403, detail="Account is locked or inactive")

        new_refresh = secrets.token_urlsafe(64)
        new_session = UserSession(
            user_id=user.id,
            refresh_token=new_refresh,
            device_info=session.device_info,
            browser=session.browser,
            os=session.os,
            ip_address=ip_address,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )
        self.db.add(new_session)
        self.db.commit()

        self._log_audit(user.id, "Refresh Token Rotation", "Success", ip_address, user_agent)

        return {
            "access_token": create_access_token(subject=str(user.id)),
            "refresh_token": new_refresh,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }

    def logout(self, refresh_token: str, ip_address: str = None, user_agent: str = None):
        session = self.db.query(UserSession).filter(UserSession.refresh_token == refresh_token).first()
        if session:
            session.is_revoked = True
            self.db.commit()
            self._log_audit(session.user_id, "Logout", "Success", ip_address, user_agent)
            
    def logout_all(self, user_id: int, ip_address: str = None, user_agent: str = None):
        self.db.query(UserSession).filter(UserSession.user_id == user_id, UserSession.is_revoked == False).update({"is_revoked": True})
        self.db.commit()
        self._log_audit(user_id, "Logout All Devices", "Success", ip_address, user_agent)

    def forgot_password(self, email: str, ip_address: str = None, user_agent: str = None):
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            # Prevent user enumeration by not revealing user doesn't exist
            return {"message": "If that email is in our database, we will send a password reset code."}
        
        self.generate_and_send_otp(user, TokenType.PASSWORD_RESET)
        self._log_audit(user.id, "Password Reset Request", "Success", ip_address, user_agent)
        return {"message": "If that email is in our database, we will send a password reset code."}

    def reset_password(self, email: str, otp: str, new_password: str, ip_address: str = None, user_agent: str = None):
        # 1. Verify OTP
        # verify_otp handles all the checks and marks it as used, so we can just call it
        self.verify_otp(email, otp, TokenType.PASSWORD_RESET, ip_address, user_agent)
        
        # 2. Find User (verify_otp succeeded, so user exists)
        user = self.db.query(User).filter(User.email == email).first()
        
        # 3. Update password
        user.password_hash = get_password_hash(new_password)
        self.db.commit()
        
        # 4. Invalidate all existing sessions (Force logout)
        self.logout_all(user.id, ip_address, user_agent)
        
        self._log_audit(user.id, "Password Reset", "Success", ip_address, user_agent)
        return {"message": "Password reset successfully. Please login with your new password."}

