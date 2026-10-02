from datetime import date

from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserRegister(BaseModel):
    role: str

    first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    last_name: str | None = Field(
        default=None,
        max_length=100,
    )

    email: EmailStr

    phone: str | None = Field(
        default=None,
        max_length=20,
    )

    institution_name: str | None = None
    education_level: str | None = None
    specialization: str | None = None
    target_role: str | None = None

    designation: str | None = None
    experience_years: float | None = None
    organization: str | None = None

    organization_name: str | None = None
    organization_type: str | None = None

    company_name: str | None = None
    industry_type: str | None = None

    website: str | None = None
    official_email: EmailStr | None = None

    password: str = Field(
        min_length=8,
        max_length=128,
    )


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: str
    is_active: bool
    is_verified: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UpdateProfileRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str

    new_password: str = Field(
        min_length=8,
        max_length=128,
    )