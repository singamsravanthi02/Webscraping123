from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from .models import UserRole
import re

# -- Shared & Base Schemas --

class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: UserRole = UserRole.STUDENT
    
    # Academic
    college: Optional[str] = None
    department: Optional[str] = None
    branch: Optional[str] = None
    semester: Optional[int] = None
    cgpa: Optional[float] = None
    skills: List[str] = Field(default_factory=list)
    career_goal: Optional[str] = None

    # Uploads & Links
    resume_url: Optional[str] = None
    profile_picture: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    
    # Legacy (if needed)
    roll_number: Optional[str] = None
    employee_id: Optional[str] = None

# -- Auth Schemas --

class UserCreate(UserBase):
    password: str = Field(..., min_length=12, description="Password must be at least 12 characters.")
    confirm_password: str
    terms_accepted: bool = Field(..., description="Must accept terms and conditions")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str):
        return _validate_password_strength(v)

    @field_validator("terms_accepted")
    @classmethod
    def terms_must_be_true(cls, v: bool):
        if not v:
            raise ValueError("Terms must be accepted")
        return v

    @model_validator(mode="after")
    def passwords_match(self):
        if self.confirm_password != self.password:
            raise ValueError("Passwords do not match")
        return self


def _validate_password_strength(v: str) -> str:
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one number')
        if not re.search(r'[^A-Za-z0-9]', v):
            raise ValueError('Password must contain at least one special character')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str

class ResendOTPRequest(BaseModel):
    email: EmailStr

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str = Field(..., min_length=12)
    confirm_password: Optional[str] = None

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str):
        return _validate_password_strength(v)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.confirm_password is not None and self.confirm_password != self.new_password:
            raise ValueError("Passwords do not match")
        return self

class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=12)
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str):
        return _validate_password_strength(v)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.confirm_password != self.new_password:
            raise ValueError("Passwords do not match")
        return self

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    college: Optional[str] = None
    department: Optional[str] = None
    branch: Optional[str] = None
    semester: Optional[int] = None
    cgpa: Optional[float] = None
    skills: Optional[List[str]] = None
    career_goal: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None

# -- Response Schemas --

class UserResponse(UserBase):
    id: int
    is_verified: bool
    is_active: bool
    is_locked: bool
    profile_completed: bool
    profile_data: Dict[str, Any]
    created_at: datetime
    last_login: Optional[datetime] = None

class SuccessResponse(BaseModel):
    message: str
