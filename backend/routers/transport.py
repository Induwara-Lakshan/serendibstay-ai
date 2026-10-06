import os
import secrets

from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from jose import jwt
from passlib.context import CryptContext

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
)

from fastapi.responses import HTMLResponse
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
)

from sqlalchemy.orm import Session

from database import get_db

from email_service import (
    send_provider_request_email,
    send_customer_status_email,
)

from models import (
    TransportProvider,
    ProviderServiceDistrict,
    TransportRequest,
)

from schemas import (
    TransportProviderCreate,
    TransportProviderLogin,
    TransportRequestCreate,
)


# =========================================================
# PASSWORD CONFIGURATION
# =========================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


# =========================================================
# JWT CONFIGURATION
# =========================================================

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")

if not ADMIN_EMAIL or not ADMIN_PASSWORD_HASH:
    raise RuntimeError("Admin credentials are not configured")

if not JWT_SECRET_KEY:
    raise RuntimeError("JWT_SECRET_KEY is not configured")


def create_provider_access_token(provider_id: int):
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(provider_id),
        "role": "transport_provider",
        "exp": expire,
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


# =========================================================
# PROVIDER AUTHENTICATION
# =========================================================

provider_security = HTTPBearer()


def create_admin_access_token():
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": "admin",
        "role": "admin",
        "exp": expire,
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


def get_current_provider(
    credentials: HTTPAuthorizationCredentials = Depends(provider_security),
    db: Session = Depends(get_db),
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )

        provider_id = payload.get("sub")
        role = payload.get("role")

        if not provider_id or role != "transport_provider":
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token",
            )

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token",
        )

    provider = (
        db.query(TransportProvider)
        .filter(TransportProvider.id == int(provider_id))
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=401,
            detail="Provider account not found",
        )

    if not provider.approved:
        raise HTTPException(
            status_code=403,
            detail="Provider account is not approved",
        )

    return provider

# =========================================================
# ADMIN AUTHENTICATION
# =========================================================




def get_current_admin(
   credentials: HTTPAuthorizationCredentials = Depends(provider_security),
):
    
    token = credentials.credentials
    print("ADMIN TOKEN RECEIVED:", token[:15])

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
        )

        admin_id = payload.get("sub")
        role = payload.get("role")

        if admin_id != "admin" or role != "admin":
            raise HTTPException(
                status_code=401,
                detail="Invalid admin authentication token",
            )

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired admin authentication token",
        )

    return {
        "sub": admin_id,
        "role": role,
    }

# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/transport",
    tags=["Transport"],
)

# =========================================================
# ADMIN LOGIN
# =========================================================

@router.post("/admin/login")
def login_admin(
    login_data: TransportProviderLogin,
):
    if login_data.email != ADMIN_EMAIL:
        raise HTTPException(
            status_code=401,
            detail="Invalid admin email or password",
        )

    if not pwd_context.verify(
        login_data.password,
        ADMIN_PASSWORD_HASH,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid admin email or password",
        )

    access_token = create_admin_access_token()

    return {
        "message": "Admin login successful",
        "access_token": access_token,
        "token_type": "bearer",
    }

# =========================================================
# PROVIDER REGISTRATION
# =========================================================

@router.post("/providers")
def register_transport_provider(
    provider: TransportProviderCreate,
    db: Session = Depends(get_db),
):
    new_provider = TransportProvider(
        provider_name=provider.provider_name,
        phone=provider.phone,
        email=provider.email,
        password_hash=pwd_context.hash(provider.password),
        vehicle_type=provider.vehicle_type,
        vehicle_number=provider.vehicle_number,
        passenger_capacity=provider.passenger_capacity,
        base_district=provider.base_district,
        approved=False,
        available=True,
    )

    db.add(new_provider)
    db.flush()

    for district in provider.service_districts:
        service_district = ProviderServiceDistrict(
            provider_id=new_provider.id,
            district=district,
        )

        db.add(service_district)

    db.commit()
    db.refresh(new_provider)

    return {
        "message": "Transport provider registered successfully",
        "provider_id": new_provider.id,
        "provider_name": new_provider.provider_name,
        "approved": new_provider.approved,
        "available": new_provider.available,
        "service_districts": provider.service_districts,
    }


# =========================================================
# PROVIDER LOGIN
# =========================================================

@router.post("/providers/login")
def login_transport_provider(
    login_data: TransportProviderLogin,
    db: Session = Depends(get_db),
):
    provider = (
        db.query(TransportProvider)
        .filter(TransportProvider.email == login_data.email)
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if not provider.password_hash:
        raise HTTPException(
            status_code=401,
            detail="Password login is not available for this provider",
        )

    if not pwd_context.verify(
        login_data.password,
        provider.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    if not provider.approved:
        raise HTTPException(
            status_code=403,
            detail="Your provider account is waiting for admin approval",
        )

    access_token = create_provider_access_token(provider.id)

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "provider": {
            "id": provider.id,
            "provider_name": provider.provider_name,
            "email": provider.email,
            "approved": provider.approved,
        },
    }


# =========================================================
# CURRENT LOGGED-IN PROVIDER
# =========================================================

@router.get("/providers/me")
def get_logged_in_provider(
    current_provider: TransportProvider = Depends(get_current_provider),
):
    return {
        "id": current_provider.id,
        "provider_name": current_provider.provider_name,
        "email": current_provider.email,
        "vehicle_type": current_provider.vehicle_type,
        "vehicle_number": current_provider.vehicle_number,
        "passenger_capacity": current_provider.passenger_capacity,
        "base_district": current_provider.base_district,
        "approved": current_provider.approved,
        "available": current_provider.available,
    }


# =========================================================
# CURRENT PROVIDER REQUESTS - JWT PROTECTED
# =========================================================

@router.get("/providers/me/requests")
def get_logged_in_provider_requests(
    current_provider: TransportProvider = Depends(get_current_provider),
    db: Session = Depends(get_db),
):
    requests = (
        db.query(TransportRequest)
        .filter(
            TransportRequest.provider_id == current_provider.id
        )
        .order_by(TransportRequest.id.desc())
        .all()
    )

    return [
        {
            "id": request.id,
            "provider_id": request.provider_id,
            "customer_name": request.customer_name,
            "customer_email": request.customer_email,
            "customer_phone": request.customer_phone,
            "pickup_location": request.pickup_location,
            "destination": request.destination,
            "pickup_date": request.pickup_date,
            "pickup_time": request.pickup_time,
            "passengers": request.passengers,
            "status": request.status,
        }
        for request in requests
    ]

# =========================================================
# UPDATE CURRENT PROVIDER AVAILABILITY - JWT PROTECTED
# =========================================================

@router.patch("/providers/me/availability")
def update_logged_in_provider_availability(
    available: bool,
    current_provider: TransportProvider = Depends(get_current_provider),
    db: Session = Depends(get_db),
):
    current_provider.available = available

    db.commit()
    db.refresh(current_provider)

    return {
        "message": (
            "Provider is now available"
            if current_provider.available
            else "Provider is now unavailable"
        ),
        "provider_id": current_provider.id,
        "available": current_provider.available,
    }

# =========================================================
# SECURE PROVIDER ACCEPT REQUEST
# =========================================================

@router.patch("/providers/me/requests/{request_id}/accept")
def accept_logged_in_provider_request(
    request_id: int,
    current_provider: TransportProvider = Depends(get_current_provider),
    db: Session = Depends(get_db),
):
    transport_request = (
        db.query(TransportRequest)
        .filter(
            TransportRequest.id == request_id,
            TransportRequest.provider_id == current_provider.id,
        )
        .first()
    )

    if not transport_request:
        raise HTTPException(
            status_code=404,
            detail="Transport request not found for this provider",
        )

    if transport_request.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Transport request is already {transport_request.status}",
        )

    transport_request.status = "accepted"

    # Disable the old email response link because the provider
    # has already responded through the authenticated dashboard.
    transport_request.response_token = None

    db.commit()
    db.refresh(transport_request)

    try:
        send_customer_status_email(
            to_email=transport_request.customer_email,
            customer_name=transport_request.customer_name,
            request_id=transport_request.id,
            status=transport_request.status,
            pickup_location=transport_request.pickup_location,
            destination=transport_request.destination,
            pickup_date=transport_request.pickup_date,
            pickup_time=transport_request.pickup_time,
        )
    except Exception as error:
        print(f"Customer email failed: {error}")

    return {
        "message": "Transport request accepted successfully",
        "request_id": transport_request.id,
        "provider_id": current_provider.id,
        "status": transport_request.status,
    }


# =========================================================
# SECURE PROVIDER REJECT REQUEST
# =========================================================

@router.patch("/providers/me/requests/{request_id}/reject")
def reject_logged_in_provider_request(
    request_id: int,
    current_provider: TransportProvider = Depends(get_current_provider),
    db: Session = Depends(get_db),
):
    transport_request = (
        db.query(TransportRequest)
        .filter(
            TransportRequest.id == request_id,
            TransportRequest.provider_id == current_provider.id,
        )
        .first()
    )

    if not transport_request:
        raise HTTPException(
            status_code=404,
            detail="Transport request not found for this provider",
        )

    if transport_request.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Transport request is already {transport_request.status}",
        )

    transport_request.status = "rejected"

    # Disable the old email response link.
    transport_request.response_token = None

    db.commit()
    db.refresh(transport_request)

    try:
        send_customer_status_email(
            to_email=transport_request.customer_email,
            customer_name=transport_request.customer_name,
            request_id=transport_request.id,
            status=transport_request.status,
            pickup_location=transport_request.pickup_location,
            destination=transport_request.destination,
            pickup_date=transport_request.pickup_date,
            pickup_time=transport_request.pickup_time,
        )
    except Exception as error:
        print(f"Customer email failed: {error}")

    return {
        "message": "Transport request rejected successfully",
        "request_id": transport_request.id,
        "provider_id": current_provider.id,
        "status": transport_request.status,
    }


# =========================================================
# SEARCH TRANSPORT PROVIDERS
# =========================================================

@router.get("/search")
def search_transport_providers(
    district: str,
    passengers: int = 1,
    db: Session = Depends(get_db),
):
    providers = (
        db.query(TransportProvider)
        .join(
            ProviderServiceDistrict,
            TransportProvider.id == ProviderServiceDistrict.provider_id,
        )
        .filter(
            ProviderServiceDistrict.district.ilike(district),
            TransportProvider.passenger_capacity >= passengers,
            TransportProvider.approved == True,
            TransportProvider.available == True,
        )
        .all()
    )

    results = []

    for provider in providers:
        service_districts = (
            db.query(ProviderServiceDistrict)
            .filter(
                ProviderServiceDistrict.provider_id == provider.id
            )
            .all()
        )

        results.append({
            "id": provider.id,
            "provider_name": provider.provider_name,
            "phone": provider.phone,
            "email": provider.email,
            "vehicle_type": provider.vehicle_type,
            "vehicle_number": provider.vehicle_number,
            "passenger_capacity": provider.passenger_capacity,
            "base_district": provider.base_district,
            "service_districts": [
                item.district
                for item in service_districts
            ],
            "approved": provider.approved,
            "available": provider.available,
        })

    return results


# =========================================================
# APPROVE PROVIDER
# =========================================================

@router.patch("/providers/{provider_id}/approve")
def approve_transport_provider(
    provider_id: int,
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    provider = (
        db.query(TransportProvider)
        .filter(TransportProvider.id == provider_id)
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Transport provider not found",
        )

    provider.approved = True

    db.commit()
    db.refresh(provider)

    return {
        "message": "Transport provider approved successfully",
        "provider_id": provider.id,
        "provider_name": provider.provider_name,
        "approved": provider.approved,
    }


# =========================================================
# GET PROVIDER BY ID
# =========================================================

@router.get("/providers/{provider_id}")
def get_transport_provider(
    provider_id: int,
    db: Session = Depends(get_db),
):
    provider = (
        db.query(TransportProvider)
        .filter(TransportProvider.id == provider_id)
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Transport provider not found",
        )

    service_districts = (
        db.query(ProviderServiceDistrict)
        .filter(
            ProviderServiceDistrict.provider_id == provider.id
        )
        .all()
    )

    return {
        "id": provider.id,
        "provider_name": provider.provider_name,
        "phone": provider.phone,
        "email": provider.email,
        "vehicle_type": provider.vehicle_type,
        "vehicle_number": provider.vehicle_number,
        "passenger_capacity": provider.passenger_capacity,
        "base_district": provider.base_district,
        "service_districts": [
            item.district
            for item in service_districts
        ],
        "approved": provider.approved,
        "available": provider.available,
    }


# =========================================================
# CREATE TRANSPORT REQUEST
# =========================================================

@router.post("/requests")
@router.post("/requests")
def create_transport_request(
    request: TransportRequestCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    provider = (
        db.query(TransportProvider)
        .filter(TransportProvider.id == request.provider_id)
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Transport provider not found",
        )

    if not provider.approved:
        raise HTTPException(
            status_code=400,
            detail="Transport provider is not approved",
        )

    if not provider.available:
        raise HTTPException(
            status_code=400,
            detail="Transport provider is not available",
        )

    if request.passengers > provider.passenger_capacity:
        raise HTTPException(
            status_code=400,
            detail="Passenger count exceeds vehicle capacity",
        )

    response_token = secrets.token_urlsafe(32)

    new_request = TransportRequest(
        provider_id=request.provider_id,
        customer_name=request.customer_name,
        customer_email=request.customer_email,
        customer_phone=request.customer_phone,
        pickup_location=request.pickup_location,
        destination=request.destination,
        pickup_date=request.pickup_date,
        pickup_time=request.pickup_time,
        passengers=request.passengers,
        status="pending",
        response_token=response_token,
    )

    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    background_tasks.add_task(
    send_provider_request_email,
    to_email=provider.email,
    request_id=new_request.id,
    customer_name=new_request.customer_name,
    customer_phone=new_request.customer_phone,
    pickup_location=new_request.pickup_location,
    destination=new_request.destination,
    pickup_date=new_request.pickup_date,
    pickup_time=new_request.pickup_time,
    passengers=new_request.passengers,
    response_token=new_request.response_token,
)

    return {
        "message": "Transport request created successfully",
        "request_id": new_request.id,
        "provider_id": new_request.provider_id,
        "provider_name": provider.provider_name,
        "pickup_location": new_request.pickup_location,
        "destination": new_request.destination,
        "pickup_date": new_request.pickup_date,
        "pickup_time": new_request.pickup_time,
        "passengers": new_request.passengers,
        "status": new_request.status,
    }


# =========================================================
# OLD PROVIDER REQUEST ENDPOINT
# Keep this for compatibility for now.
# =========================================================

@router.get("/providers/{provider_id}/requests")
def get_provider_transport_requests(
    provider_id: int,
    db: Session = Depends(get_db),
):
    provider = (
        db.query(TransportProvider)
        .filter(TransportProvider.id == provider_id)
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Transport provider not found",
        )

    requests = (
        db.query(TransportRequest)
        .filter(
            TransportRequest.provider_id == provider_id
        )
        .all()
    )

    return [
        {
            "id": request.id,
            "provider_id": request.provider_id,
            "customer_name": request.customer_name,
            "customer_email": request.customer_email,
            "customer_phone": request.customer_phone,
            "pickup_location": request.pickup_location,
            "destination": request.destination,
            "pickup_date": request.pickup_date,
            "pickup_time": request.pickup_time,
            "passengers": request.passengers,
            "status": request.status,
        }
        for request in requests
    ]


# =========================================================
# OLD ACCEPT TRANSPORT REQUEST
# Keep for compatibility for now.
# =========================================================

@router.patch("/requests/{request_id}/accept")
def accept_transport_request(
    request_id: int,
    db: Session = Depends(get_db),
):
    transport_request = (
        db.query(TransportRequest)
        .filter(TransportRequest.id == request_id)
        .first()
    )

    if not transport_request:
        raise HTTPException(
            status_code=404,
            detail="Transport request not found",
        )

    if transport_request.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Transport request is already {transport_request.status}",
        )

    transport_request.status = "accepted"

    db.commit()
    db.refresh(transport_request)

    return {
        "message": "Transport request accepted successfully",
        "request_id": transport_request.id,
        "provider_id": transport_request.provider_id,
        "status": transport_request.status,
    }


# =========================================================
# OLD REJECT TRANSPORT REQUEST
# Keep for compatibility for now.
# =========================================================

@router.patch("/requests/{request_id}/reject")
def reject_transport_request(
    request_id: int,
    db: Session = Depends(get_db),
):
    transport_request = (
        db.query(TransportRequest)
        .filter(TransportRequest.id == request_id)
        .first()
    )

    if not transport_request:
        raise HTTPException(
            status_code=404,
            detail="Transport request not found",
        )

    if transport_request.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Transport request is already {transport_request.status}",
        )

    transport_request.status = "rejected"

    db.commit()
    db.refresh(transport_request)

    return {
        "message": "Transport request rejected successfully",
        "request_id": transport_request.id,
        "provider_id": transport_request.provider_id,
        "status": transport_request.status,
    }


# =========================================================
# EMAIL RESPONSE CONFIRMATION PAGE
# =========================================================

@router.get("/respond", response_class=HTMLResponse)
def transport_response_confirmation(
    request_id: int,
    action: str,
    token: str,
    db: Session = Depends(get_db),
):
    if action not in ["accept", "reject"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid action",
        )

    transport_request = (
        db.query(TransportRequest)
        .filter(
            TransportRequest.id == request_id,
            TransportRequest.response_token == token,
        )
        .first()
    )

    if not transport_request:
        raise HTTPException(
            status_code=404,
            detail="Invalid or expired transport request link",
        )

    if transport_request.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Transport request is already {transport_request.status}",
        )

    action_title = (
        "Accept"
        if action == "accept"
        else "Reject"
    )

    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>SerendibStay AI - Transport Request</title>
        </head>

        <body style="
            font-family: Arial, sans-serif;
            background: #f4f6f8;
            padding: 40px;
        ">

            <div style="
                max-width: 600px;
                margin: auto;
                background: white;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            ">

                <h2>SerendibStay AI</h2>

                <h3>
                    Transport Request #{transport_request.id}
                </h3>

                <p>
                    <strong>Customer:</strong>
                    {transport_request.customer_name}
                </p>

                <p>
                    <strong>Pickup:</strong>
                    {transport_request.pickup_location}
                </p>

                <p>
                    <strong>Destination:</strong>
                    {transport_request.destination}
                </p>

                <p>
                    <strong>Date:</strong>
                    {transport_request.pickup_date}
                </p>

                <p>
                    <strong>Time:</strong>
                    {transport_request.pickup_time}
                </p>

                <p>
                    <strong>Passengers:</strong>
                    {transport_request.passengers}
                </p>

                <p>
                    <strong>Current Status:</strong>
                    {transport_request.status}
                </p>

                <hr>

                <h3>
                    Confirm {action_title} Request?
                </h3>

                <form
                    method="post"
                    action="/transport/respond/confirm?request_id={transport_request.id}&action={action}&token={token}"
                >
                    <button
                        type="submit"
                        style="
                            padding: 12px 25px;
                            font-size: 16px;
                            cursor: pointer;
                        "
                    >
                        Confirm {action_title}
                    </button>
                </form>

            </div>

        </body>
        </html>
        """
    )


# =========================================================
# CONFIRM EMAIL RESPONSE
# =========================================================

@router.post("/respond/confirm")
def confirm_transport_response(
    request_id: int,
    action: str,
    token: str,
    db: Session = Depends(get_db),
):
    if action not in ["accept", "reject"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid action",
        )

    transport_request = (
        db.query(TransportRequest)
        .filter(
            TransportRequest.id == request_id,
            TransportRequest.response_token == token,
        )
        .first()
    )

    if not transport_request:
        raise HTTPException(
            status_code=404,
            detail="Invalid or expired transport request",
        )

    if transport_request.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Request has already been {transport_request.status}",
        )

    if action == "accept":
        transport_request.status = "accepted"
    else:
        transport_request.status = "rejected"

    transport_request.response_token = None

    db.commit()
    db.refresh(transport_request)

    try:
        send_customer_status_email(
            to_email=transport_request.customer_email,
            customer_name=transport_request.customer_name,
            request_id=transport_request.id,
            status=transport_request.status,
            pickup_location=transport_request.pickup_location,
            destination=transport_request.destination,
            pickup_date=transport_request.pickup_date,
            pickup_time=transport_request.pickup_time,
        )
    except Exception as error:
        print(f"Customer email failed: {error}")

    return {
        "message": (
            f"Transport request "
            f"{transport_request.status} successfully"
        ),
        "request_id": transport_request.id,
        "status": transport_request.status,
    }


# =========================================================
# ADMIN - GET ALL PROVIDERS
# =========================================================

@router.get("/providers")
def get_all_transport_providers(
    admin: dict = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    providers = (
        db.query(TransportProvider)
        .order_by(TransportProvider.id.desc())
        .all()
    )

    result = []

    for provider in providers:
        service_districts = (
            db.query(ProviderServiceDistrict)
            .filter(
                ProviderServiceDistrict.provider_id == provider.id
            )
            .all()
        )

        result.append({
            "id": provider.id,
            "provider_name": provider.provider_name,
            "phone": provider.phone,
            "email": provider.email,
            "vehicle_type": provider.vehicle_type,
            "vehicle_number": provider.vehicle_number,
            "passenger_capacity": provider.passenger_capacity,
            "base_district": provider.base_district,
            "service_districts": [
                district.district
                for district in service_districts
            ],
            "approved": provider.approved,
            "available": provider.available,
        })

    return result