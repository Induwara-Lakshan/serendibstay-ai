
import os

import hmac
from fastapi import Request

from urllib.parse import urlparse
import hashlib


import uuid
from fastapi import status



from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Booking, Hotel, Payment

load_dotenv("/app/.env")

router = APIRouter(prefix="/payments/payhere", tags=["PayHere Payments"])

DEMO_HOTEL_ID = 1
DEMO_PRICE_LKR = Decimal("1000.00")


def require_sandbox():
    if os.getenv("PAYHERE_SANDBOX", "").lower() != "true":
        raise HTTPException(
            status_code=503,
            detail="PayHere sandbox payments are disabled"
        )


def get_payhere_urls():
    keys = (
        "PAYHERE_NOTIFY_URL",
        "PAYHERE_RETURN_URL",
        "PAYHERE_CANCEL_URL",
    )

    urls = {}

    for key in keys:
        value = os.getenv(key, "").strip()
        parsed = urlparse(value)

        if (
            parsed.scheme not in ("http", "https")
            or not parsed.netloc
            or parsed.username
            or parsed.password
        ):
            raise HTTPException(
                status_code=503,
                detail=f"{key} is not configured correctly"
            )

        if key == "PAYHERE_NOTIFY_URL" and parsed.scheme != "https":
            raise HTTPException(
                status_code=503,
                detail="PayHere notify URL must use HTTPS"
            )

        urls[key] = value

    return urls




from datetime import date
from pydantic import BaseModel, Field, EmailStr, model_validator


class PayHereCheckoutRequest(BaseModel):
    hotel_id: int = Field(gt=0)
    customer_name: str = Field(min_length=1, max_length=150)
    customer_email: EmailStr

    customer_phone: str = Field(min_length=9, max_length=15, pattern=r"^\+?[0-9]{9,15}$")


    customer_address: str = Field(min_length=3, max_length=255)
    customer_city: str = Field(min_length=2, max_length=100)
    customer_country: str = Field(default="Sri Lanka", min_length=2, max_length=100)


    check_in: date
    check_out: date

    @model_validator(mode="after")
    def validate_booking_dates(self):
        if self.check_in < date.today():
            raise ValueError("Check-in date cannot be in the past")

        if self.check_out <= self.check_in:
            raise ValueError("Check-out date must be after check-in date")

        return self


def calculate_demo_amount(hotel_id: int, check_in: date, check_out: date):
    require_sandbox()

    configured_hotel_id = int(
        os.getenv("PAYHERE_DEMO_HOTEL_ID", "1")
    )

    price_per_night = Decimal(
        os.getenv("PAYHERE_DEMO_PRICE_LKR", "1000.00")
    )

    if hotel_id != configured_hotel_id:
        raise HTTPException(
            status_code=403,
            detail="Demo payments are only available for the selected test hotel"
        )

    nights = (check_out - check_in).days

    if nights <= 0:
        raise HTTPException(
            status_code=422,
            detail="Invalid booking dates"
        )

    if price_per_night <= 0:
        raise HTTPException(
            status_code=503,
            detail="Invalid demo payment configuration"
        )

    total_amount = price_per_night * nights

    return {
        "nights": nights,
        "price_per_night": price_per_night,
        "total_amount": total_amount,
        "currency": "LKR",
        "is_demo_price": True
    }



def split_customer_name(full_name: str):
    parts = full_name.strip().split(maxsplit=1)

    first_name = parts[0] if parts else ""
    last_name = parts[1] if len(parts) > 1 else "-"

    return first_name, last_name


def generate_payhere_hash(
    merchant_id: str,
    order_id: str,
    amount: Decimal,
    currency: str,
    merchant_secret: str
) -> str:
    formatted_amount = f"{amount:.2f}"

    secret_hash = hashlib.md5(
        merchant_secret.encode("utf-8")
    ).hexdigest().upper()

    hash_string = (
        merchant_id
        + order_id
        + formatted_amount
        + currency
        + secret_hash
    )

    return hashlib.md5(
        hash_string.encode("utf-8")
    ).hexdigest().upper()



def verify_payhere_callback_signature(
    merchant_id: str,
    order_id: str,
    payhere_amount: str,
    payhere_currency: str,
    status_code: str,
    received_md5sig: str,
    merchant_secret: str,
) -> bool:
    secret_hash = hashlib.md5(
        merchant_secret.encode("utf-8")
    ).hexdigest().upper()

    signature_string = (
        merchant_id
        + order_id
        + payhere_amount
        + payhere_currency
        + status_code
        + secret_hash
    )

    expected_md5sig = hashlib.md5(
        signature_string.encode("utf-8")
    ).hexdigest().upper()

    return hmac.compare_digest(
        expected_md5sig,
        received_md5sig.strip().upper()
    )


@router.post("/checkout", status_code=status.HTTP_201_CREATED)
def create_payhere_checkout(
    data: PayHereCheckoutRequest,
    db: Session = Depends(get_db)
):


    require_sandbox()
    payment_urls = get_payhere_urls()

    hotel = db.query(Hotel).filter(
        Hotel.id == data.hotel_id
    ).first()



    hotel = db.query(Hotel).filter(
        Hotel.id == data.hotel_id
    ).first()

    if hotel is None:
        raise HTTPException(
            status_code=404,
            detail="Hotel not found"
        )

    if (
        hotel.verification_status not in ("legacy", "verified")
        or hotel.is_active is not True
        or hotel.available is not True
    ):
        raise HTTPException(
            status_code=409,
            detail="Hotel is not available for booking"
        )

    pricing = calculate_demo_amount(
        data.hotel_id,
        data.check_in,
        data.check_out
    )

    merchant_id = os.getenv("PAYHERE_MERCHANT_ID")
    merchant_secret = os.getenv("PAYHERE_MERCHANT_SECRET")

    if not merchant_id or not merchant_secret:
        raise HTTPException(
            status_code=503,
            detail="PayHere configuration is missing"
        )

    order_id = f"DEMO-{uuid.uuid4().hex}"

    first_name, last_name = split_customer_name(data.customer_name)

    booking = Booking(
        hotel_id=data.hotel_id,
        customer_name=data.customer_name,
        customer_email=data.customer_email,
        check_in=data.check_in,
        check_out=data.check_out,
        status="pending"
    )

    try:
        db.add(booking)
        db.flush()

        payment = Payment(
            booking_id=booking.id,
            order_id=order_id,
            amount=pricing["total_amount"],
            currency="LKR",
            status="pending"
        )

        db.add(payment)
        db.commit()

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to create payment checkout"
        )

    payment_hash = generate_payhere_hash(
        merchant_id=merchant_id,
        order_id=order_id,
        amount=pricing["total_amount"],
        currency="LKR",
        merchant_secret=merchant_secret
    )


    return {
    "checkout_url": "https://sandbox.payhere.lk/pay/checkout",
    "merchant_id": merchant_id,
     "first_name": first_name,
    "last_name": last_name,
    "email": data.customer_email,
    "phone": data.customer_phone,
    "address": data.customer_address,
    "city": data.customer_city,
   "country": data.customer_country,


    "notify_url": payment_urls["PAYHERE_NOTIFY_URL"],
    "return_url": payment_urls["PAYHERE_RETURN_URL"],
    "cancel_url": payment_urls["PAYHERE_CANCEL_URL"],
        "order_id": order_id,
        "amount": f'{pricing["total_amount"]:.2f}',
        "currency": "LKR",
        "hash": payment_hash,
        "booking_id": booking.id,
        "hotel_name": hotel.name,
        "items": f"Demo Hotel Booking - {hotel.name}",

        "nights": pricing["nights"],
        "is_demo_price": True,
        "message": "Sandbox demo checkout created. Booking is pending payment verification."
    }


@router.post("/notify")
async def payhere_notify(
    request: Request,
    db: Session = Depends(get_db),
):
    require_sandbox()

    form = await request.form()

    merchant_id = str(form.get("merchant_id", ""))
    order_id = str(form.get("order_id", ""))
    payhere_amount = str(form.get("payhere_amount", ""))
    payhere_currency = str(form.get("payhere_currency", ""))
    status_code = str(form.get("status_code", ""))
    received_md5sig = str(form.get("md5sig", ""))

    merchant_secret = os.getenv("PAYHERE_MERCHANT_SECRET", "").strip()
    expected_merchant_id = os.getenv("PAYHERE_MERCHANT_ID", "").strip()

    if not merchant_secret or not expected_merchant_id:
        raise HTTPException(
            status_code=503,
            detail="PayHere merchant configuration is missing"
        )

    if merchant_id != expected_merchant_id:
        raise HTTPException(
            status_code=400,
            detail="Invalid merchant ID"
        )

    if not verify_payhere_callback_signature(
        merchant_id,
        order_id,
        payhere_amount,
        payhere_currency,
        status_code,
        received_md5sig,
        merchant_secret,
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid PayHere signature"
        )

    payment = db.query(Payment).filter(
        Payment.order_id == order_id
    ).first()

    if payment is None:
        raise HTTPException(
            status_code=404,
            detail="Payment order not found"
        )

    try:
        received_amount = Decimal(payhere_amount)
    except (InvalidOperation, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Invalid payment amount"
        )

    if (
        not received_amount.is_finite()
        or received_amount != payment.amount
    ):
        raise HTTPException(
            status_code=400,
            detail="Payment amount mismatch"
        )

    if (
        payhere_currency != "LKR"
        or payment.currency != "LKR"
        or payhere_currency != payment.currency
    ):
        raise HTTPException(
            status_code=400,
            detail="Payment currency mismatch"
        )


    payhere_payment_id = str(form.get("payment_id", "")).strip()

    if status_code == "2":
        new_payment_status = "success"
        new_booking_status = "confirmed"
    elif status_code == "-1":
        new_payment_status = "cancelled"
        new_booking_status = "cancelled"
    elif status_code in ("-2", "-3"):
        new_payment_status = "failed"
        new_booking_status = "cancelled"
    elif status_code == "0":
        return {"message": "Payment is still pending"}
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported PayHere payment status"
        )

    try:
        locked_payment = db.query(Payment).filter(
            Payment.order_id == order_id
        ).with_for_update().first()

        if locked_payment is None:
            raise HTTPException(
                status_code=404,
                detail="Payment order not found"
            )


        if (
            not received_amount.is_finite()
            or received_amount != locked_payment.amount
            or payhere_currency != locked_payment.currency
            or locked_payment.currency != "LKR"
        ):
            raise HTTPException(
                status_code=400,
                detail="Payment amount or currency mismatch"
            )


        booking = db.query(Booking).filter(
            Booking.id == locked_payment.booking_id
        ).with_for_update().first()

        if booking is None:
            raise HTTPException(
                status_code=404,
                detail="Booking not found"
            )

        if locked_payment.status != "pending":
            db.rollback()
            return {"message": "Payment already processed"}


        if new_payment_status == "success" and not payhere_payment_id:
            raise HTTPException(
                status_code=400,
                detail="Missing PayHere payment ID"
            )

        if payhere_payment_id:
            existing_payment = db.query(Payment).filter(
                Payment.payhere_payment_id == payhere_payment_id,
                Payment.id != locked_payment.id
            ).first()

            if existing_payment is not None:
                raise HTTPException(
                    status_code=409,
                    detail="PayHere payment ID already belongs to another order"
                )


        locked_payment.status = new_payment_status
        locked_payment.payhere_payment_id = payhere_payment_id or None
        booking.status = new_booking_status

        db.commit()

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Unable to process PayHere notification"
        )

    return {"message": "Payment notification processed successfully"}
