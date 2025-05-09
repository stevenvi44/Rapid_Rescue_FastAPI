import os
import logging
from schemas import UserCreate, ForgotPasswordRequest
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from src.database import get_db
from src.models.db_models import User
from src.schemas import UserCreate
from dotenv import load_dotenv
import random
from schemas import VerifyCode

# ------------------- Logging Setup -------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------- Environment Variables -------------------
SECRET_KEY = "26fb81bf2adbda2b225009d386e156fa0979451294ba06963fb11907011cc0fc"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
EMAIL_TOKEN_EXPIRE_MINUTES = 15

load_dotenv()
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ------------------- Password Hashing -------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# ------------------- Email Configuration -------------------
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)

mail = FastMail(conf)
router = APIRouter(prefix="/auth", tags=["Authentication"])

# ------------------- Token Handling -------------------
def create_token(data: dict, expires_delta: timedelta):
    expire = datetime.now(timezone.utc) + expires_delta
    data.update({"exp": expire})
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def create_access_token(user: User):
    return create_token({"sub": user.email, "role": user.role}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))

def create_refresh_token(user: User):
    return create_token({"sub": user.email}, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))

# ------------------- Password Handling -------------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# ------------------- Email Sending -------------------
async def send_email_background(background_tasks: BackgroundTasks, subject: str, email: str, body: str):
    try:
        message = MessageSchema(
            subject=subject,
            recipients=[email],
            body=body,
            subtype="html"
        )

        # Debugging - Print email details
        print(f"📨 Preparing to send email to {email}...")
        print(f"📧 Subject: {subject}")
        print(f"📨 Email Body: {body}")

        # Send email
        background_tasks.add_task(mail.send_message, message)

        print(f"✅ Email task added successfully to {email}")
    except Exception as e:
        print(f"❌ Failed to send email: {str(e)}")  # Debugging error

# ------------------- User Authentication -------------------
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")

        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = db.query(User).filter(User.email == email).first()
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")

        return user

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ------------------- User Registration -------------------
@router.post("/register")
async def register_user(user_data: UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    hashed_password = hash_password(user_data.password)
    verification_code = str(random.randint(100000, 999999))  # Generate a 6-digit OTP

    new_user = User(
        username=user_data.username,
        email=user_data.email,
        phone_number=user_data.phone_number,
        password=hashed_password,
        location=user_data.location,
        is_active=False,
        verification_code=verification_code,  # Store OTP in DB
        role="user"
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Send OTP via email
    email_body = f"Your email verification code is: {verification_code}"
    await send_email_background(background_tasks, "Verify Your Email", new_user.email, email_body)

    return {"message": "Registration successful. Please check your email for the verification code."}

@router.post("/verify-email")
def verify_email(data: VerifyCode, db: Session = Depends(get_db)):
    """
    Verify email using email and verification code (OTP).
    """
    user = db.query(User).filter(User.email == data.email, User.verification_code == data.code).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid email or verification code")

    user.is_active = True
    user.verification_code = None  # Remove the code after verification
    db.commit()

    return {"message": "Email verified successfully. You can now log in."}

# ------------------- Login & Refresh Token -------------------
@router.post("/login")
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        (User.email == form_data.username) | (User.username == form_data.username)
    ).first()

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Please verify your email first")

    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user_id": user.user_id,
        "username": user.username,
        "role": user.role
    }


@router.post("/refresh")
def refresh_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        new_access_token = create_token({"sub": email}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        return {"access_token": new_access_token, "token_type": "bearer"}
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid refresh token")


# ------------------- Forgot Password -------------------
@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reset_code = str(random.randint(100000, 999999))  # Generate a reset OTP
    user.verification_code = reset_code  # Store OTP in DB
    db.commit()

    email_body = f"Your password reset code is: {reset_code}"
    await send_email_background(background_tasks, "Reset Your Password", user.email, email_body)

    return {"message": "Password reset code has been sent to your email."}

@router.post("/reset-password")
def reset_password(token: str, new_password: str, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")

        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.password = hash_password(new_password)
        db.commit()

        return {"message": "Password has been successfully reset"}

    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

def get_admin_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = get_current_user(token, db)

    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    return user