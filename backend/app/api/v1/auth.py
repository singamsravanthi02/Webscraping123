from fastapi import APIRouter, Depends, Request, Form
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from app.core.rate_limit import RateLimiterWrapper as RateLimiter

from app.db.session import get_db
from app.core.config import settings
from app.domain.users.schemas import (
    UserCreate, UserLogin, TokenResponse, 
    VerifyOTPRequest, ResendOTPRequest,
    ForgotPasswordRequest, ResetPasswordRequest,
    SuccessResponse
)
from app.domain.users.models import TokenType
from app.services.auth_service import AuthService
from app.api.dependencies.auth import get_current_user
from app.domain.users.models import User

router = APIRouter()

@router.post("/register", response_model=Dict[str, Any], status_code=201, dependencies=[Depends(RateLimiter(times=5, seconds=60))])
def register(user_in: UserCreate, request: Request, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    user = auth_service.register_user(user_in, ip_address, user_agent)
    if settings.ENABLE_EMAIL_VERIFICATION:
        return {"message": "Registration successful. Please check your email for the OTP."}
    return {"message": "Registration successful. You can sign in now."}

@router.post("/verify-otp", response_model=SuccessResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
def verify_otp(req: VerifyOTPRequest, request: Request, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return auth_service.verify_otp(req.email, req.otp, TokenType.EMAIL_VERIFICATION, ip_address, user_agent)

@router.post("/resend-otp", response_model=SuccessResponse, dependencies=[Depends(RateLimiter(times=3, seconds=60))])
def resend_otp(req: ResendOTPRequest, request: Request, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return auth_service.resend_otp(req.email, TokenType.EMAIL_VERIFICATION, ip_address, user_agent)

@router.post("/login", response_model=TokenResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
def login(login_data: UserLogin, request: Request, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    ip_address = request.client.host if request.client else None
    device_info = request.headers.get("user-agent")
    return auth_service.login(login_data, ip_address, device_info)

@router.post("/login/access-token", response_model=TokenResponse, dependencies=[Depends(RateLimiter(times=10, seconds=60))])
def login_access_token(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    auth_service = AuthService(db)
    ip_address = request.client.host if request.client else None
    device_info = request.headers.get("user-agent")
    login_data = UserLogin(email=username, password=password)
    try:
        return auth_service.login(login_data, ip_address, device_info)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail)
        raise

@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: Request, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    refresh_token_str = request.headers.get("x-refresh-token")
    if not refresh_token_str:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Refresh token required in headers")
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return auth_service.refresh_token(refresh_token_str, ip_address, user_agent)

@router.post("/logout", response_model=SuccessResponse)
def logout(request: Request, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    refresh_token_str = request.headers.get("x-refresh-token")
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    if refresh_token_str:
        auth_service.logout(refresh_token_str, ip_address, user_agent)
    return {"message": "Logged out successfully"}

@router.post("/logout-all", response_model=SuccessResponse)
def logout_all(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    auth_service.logout_all(current_user.id, ip_address, user_agent)
    return {"message": "Logged out of all devices successfully"}

@router.post("/forgot-password", response_model=SuccessResponse, dependencies=[Depends(RateLimiter(times=3, seconds=60))])
def forgot_password(req: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return auth_service.forgot_password(req.email, ip_address, user_agent)

@router.post("/reset-password", response_model=SuccessResponse, dependencies=[Depends(RateLimiter(times=5, seconds=60))])
def reset_password(req: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return auth_service.reset_password(req.email, req.otp, req.new_password, ip_address, user_agent)

from pydantic import BaseModel
class GoogleAuthRequest(BaseModel):
    code: str

@router.get("/google/login", response_model=Dict[str, str])
def get_google_login_url(db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    return {"url": auth_service.get_google_login_url()}

@router.post("/google/callback", response_model=TokenResponse)
async def google_callback(req: GoogleAuthRequest, request: Request, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    ip_address = request.client.host if request.client else None
    device_info = request.headers.get("user-agent")
    return await auth_service.google_callback(req.code, ip_address, device_info)
