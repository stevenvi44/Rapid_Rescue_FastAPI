from pydantic import BaseModel, EmailStr, StringConstraints, HttpUrl, Field, model_validator, field_validator # BaseModel for defining schemas
from typing import Optional, Annotated # Optional allows fields to be nullable.
from datetime import datetime, date, timezone
from decimal import Decimal
from enum import Enum
import re

# User Schema
class UserBase(BaseModel):
    username: str
    email: EmailStr
    phone_number: Annotated[str, StringConstraints(pattern=r"^(\+20|0)?(10|11|12|15)[0-9]{8}$", max_length=13)] # regular expression EGY
    location: str
    role: str

class UserCreate(UserBase): # This field is not in UserBase since we don’t want to expose it in responses
    password: Annotated[str, StringConstraints(min_length=8, pattern=r"^[A-Za-z\d@#$%^&+=!]{8,}$")] # (A-Z), (a-z), (0-9), (@#$%^&+=! or similar), Minimum 8 characters

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[Annotated[str, StringConstraints(pattern=r"^(\+20|0)?(10|11|12|15)[0-9]{8}$", max_length=13)]] = None
    location: Optional[str] = None
    role: Optional[str] = None
    password: Optional[Annotated[str, StringConstraints(min_length=8, pattern=r"^[A-Za-z\d@#$%^&+=!]{8,}$")]] = None
    reset_token: Optional[str] = None

    class Config:
        from_attributes = True  # Enables ORM-like behavior for SQLAlchemy models

class UserResponse(UserBase):
    user_id: int
    reset_token: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True

# Car Schema
class CarBase(BaseModel):
    make: str
    model: str
    logo_url: Optional[str] = None
    car_image_url: Optional[str] = None

class CarCreate(CarBase):
    pass

class CarUpdate(BaseModel):
    make: Optional[str] = None
    model: Optional[str] = None
    logo_url: Optional[str] = None
    car_image_url: Optional[str] = None

    class Config:
        from_attributes = True

class CarResponse(BaseModel):
    car_id: int
    make: str
    model: str
    logo_url: Optional[str] = None
    car_image_url: Optional[str] = None

    @field_validator("logo_url")
    @classmethod
    def format_google_drive_link(cls, v):
        if v and "drive.google.com" in v:
            match = re.search(r"/d/([a-zA-Z0-9_-]+)/", v)
            if match:
                return f"https://drive.google.com/uc?id={match.group(1)}"
        return v

    class Config:
        from_attributes = True

# UserCar Schema
class UserCarBase(BaseModel):
    user_id: int
    car_id: int
    ownership_type: Optional[Annotated[str, StringConstraints(max_length=20)]] = None # can be null
    year: Annotated[int, Field(ge=1900, le=2100)]  # Ensures a valid year range
    license_plate: Optional[Annotated[str, StringConstraints(max_length=15)]] = None
    current_mileage: Optional[Annotated[str, StringConstraints(max_length=20)]]  # Prevents negative mileage

class UserCarCreate(UserCarBase):
    pass

class UserCarUpdate(BaseModel):
    user_id: Optional[int] = None
    car_id: Optional[int] = None
    ownership_type: Optional[Annotated[str, StringConstraints(max_length=20)]] = None
    year: Optional[Annotated[int, Field(ge=1900, le=2100)]] = None
    license_plate: Optional[Annotated[str, StringConstraints(max_length=15)]] = None
    current_mileage: Optional[Annotated[str, StringConstraints(max_length=20)]] = None

class UserCarResponse(UserCarBase):
    user_car_id: int
    class Config:
        from_attributes = True

# Order Schema
class OrderStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    canceled = "canceled"

class OrderBase(BaseModel):
    user_id: int
    user_car_id: int
    order_status: OrderStatus  # Enum for better validation
    order_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc)) # Default timestamp
    total_cost: Decimal = Field(ge=0)  # Ensure cost is non-negative

class OrderCreate(OrderBase):
    pass

class OrderUpdate(BaseModel):
    user_id: Optional[int] = None
    user_car_id: Optional[int] = None
    order_status: Optional["OrderStatus"] = None  # Allow status updates
    order_date: Optional[datetime] = None
    total_cost: Optional[Decimal] = Field(None, ge=0)  # Ensure non-negative cost

    class Config:
        from_attributes = True

class OrderResponse(OrderBase):
    order_id: int
    class Config:
        from_attributes = True


# OrderService Schema
class OrderServiceBase(BaseModel):
    order_id: int
    request_id: int
    cost: Decimal = Field(ge=0)

class OrderServiceCreate(OrderServiceBase):
    pass

class OrderServiceUpdate(BaseModel):
    order_id: Optional[int] = None
    request_id: Optional[int] = None
    cost: Optional[Decimal] = Field(None, ge=0)  # Ensure non-negative cost

    class Config:
        from_attributes = True

class OrderServiceResponse(OrderServiceBase):
    order_service_id: int
    class Config:
        from_attributes = True

# OrderPart Schema
class OrderPartBase(BaseModel):
    order_id: int = Field(gt=0) # Order ID must be greater than 0
    part_id: int = Field(gt=0) # Part ID must be greater than 0
    quantity: int = Field(ge=1) # Quantity must be at least 1

class OrderPartCreate(OrderPartBase):
    pass

class OrderPartUpdate(BaseModel):
    order_id: Optional[int] = Field(None, gt=0)  # Order ID must be greater than 0
    part_id: Optional[int] = Field(None, gt=0)  # Part ID must be greater than 0
    quantity: Optional[int] = Field(None, ge=1)  # Quantity must be at least 1

    class Config:
        from_attributes = True

class OrderPartResponse(OrderPartBase):
    order_part_id: int
    class Config:
        from_attributes = True

# Spare Part Schema
class AvailabilityStatus(str, Enum):
    available = "available"
    out_of_stock = "out of stock"
    discontinued = "discontinued"

class SparePartBase(BaseModel):
    service_provider_id: int
    name: str = Field(max_length=100)
    description: str
    price: Decimal = Field(ge=0, decimal_places=2)
    availability_status: AvailabilityStatus
    photo_url: Optional[HttpUrl] = None

class SparePartCreate(SparePartBase):
    pass

class SparePartUpdate(BaseModel):
    service_provider_id: Optional[int] = None
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0, decimal_places=2)
    availability_status: Optional["AvailabilityStatus"] = None
    photo_url: Optional[HttpUrl] = None

    class Config:
        from_attributes = True

class SparePartResponse(SparePartBase):
    part_id: int
    class Config:
        from_attributes = True

# Service Provider Schema
class ServiceProviderBase(BaseModel):
    name: str = Field(max_length=100)
    email: EmailStr = Field(max_length=255)
    phone_number: Annotated[str, StringConstraints(pattern=r"^(\+20|0)?(10|11|12|15)[0-9]{8}$", max_length=13)]
    location: str = Field(max_length=255)
    contact_person: str = Field(max_length=100)
    other_details: Optional[str] = None
    filtering: str = Field(max_length=50)
    location2: str = Field(max_length=255)


class ServiceProviderCreate(ServiceProviderBase):
    pass

class ServiceProviderUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = Field(None, max_length=255)
    phone_number: Optional[Annotated[str, StringConstraints(pattern=r"^(\+20|0)?(10|11|12|15)[0-9]{8}$", max_length=13)]] = None
    location: Optional[str] = Field(None, max_length=255)
    contact_person: Optional[str] = Field(None, max_length=100)
    other_details: Optional[str] = None
    filtering: str = Field(max_length=50)
    location2: Optional[str] = Field(None, max_length=255)

    class Config:
        from_attributes = True

class ServiceProviderResponse(ServiceProviderBase):
    service_provider_id: int
    class Config:
        from_attributes = True

# Service Request Schema
class ServiceType(str, Enum):
    TOWING = "Towing"
    MAINTENANCE = "Maintenance"
    PARTS_PURCHASE = "Parts Purchase"

class ServiceStatus(str, Enum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"
    CANCELED = "Canceled"

class ServiceRequestBase(BaseModel):
    user_id: int
    user_car_id: int
    service_provider_id: int
    service_type: Optional[ServiceType] = Field(None, max_length=50)
    status: Optional[ServiceStatus] = Field(None, max_length=50)  # Nullable
    cost: float = Field(ge=0)

class ServiceRequestCreate(ServiceRequestBase):
    pass

class ServiceRequestUpdate(BaseModel):
    user_id: Optional[int] = None
    user_car_id: Optional[int] = None
    service_provider_id: Optional[int] = None
    service_type: Optional["ServiceType"] = None
    status: Optional["ServiceStatus"] = None
    cost: Optional[float] = Field(None, ge=0)  # Ensure cost is non-negative

    class Config:
        from_attributes = True

class ServiceRequestResponse(ServiceRequestBase):
    request_id: int
    class Config:
        from_attributes = True


# Transaction Schema
class PaymentMethod(str, Enum):
    cash = "cash"
    credit_card = "credit_card"
    bank_transfer = "bank_transfer"
    mobile_payment = "mobile_payment"

class PaymentStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"

class TransactionBase(BaseModel):
    order_id: int
    total_paid_amount: int = Field(..., ge=0)
    payment_method: PaymentMethod
    payment_status: PaymentStatus

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    order_id: Optional[int] = None
    total_paid_amount: Optional[int] = Field(None, ge=0)
    payment_method: Optional[PaymentMethod] = None
    payment_status: Optional[PaymentStatus] = None

    class Config:
        from_attributes = True

class TransactionResponse(TransactionBase):
    transaction_id: int
    class Config:
        from_attributes = True

# CarsSpareParts Schema
class CarsSparePartsBase(BaseModel):
    car_id: int = Field(..., ge=2)
    part_id: int = Field(..., ge=2)

class CarsSparePartsCreate(CarsSparePartsBase):
    pass

class CarsSparePartsUpdate(BaseModel):
    car_id: Optional[int] = Field(None, ge=2)
    part_id: Optional[int] = Field(None, ge=2)

    class Config:
        from_attributes = True

class CarsSparePartsResponse(CarsSparePartsBase):
    class Config:
        from_attributes = True


# ------------------- Verify Email Schema -------------------
class VerifyCode(BaseModel):
    email: EmailStr
    code: str  # 6-digit verification code

# ------------------- Forgot Password Schema -------------------
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

# ------------------- Reset Password Schema -------------------
class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str  # 6-digit reset code
    new_password: str


# AI schema
class FeatureRanges(BaseModel):
    """Custom ranges for each feature"""
    engine_rpm: tuple[float, float]
    lub_oil_pressure: tuple[float, float]
    fuel_pressure: tuple[float, float]
    coolant_pressure: tuple[float, float]
    lub_oil_temp: tuple[float, float]
    coolant_temp: tuple[float, float]
    temp_difference: tuple[float, float]

class FeatureDescriptions(BaseModel):
    """Descriptions for each feature"""
    engine_rpm: str
    lub_oil_pressure: str
    fuel_pressure: str
    coolant_pressure: str
    lub_oil_temp: str
    coolant_temp: str
    temp_difference: str
