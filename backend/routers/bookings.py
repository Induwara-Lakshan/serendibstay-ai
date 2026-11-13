from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Booking, Hotel
from schemas import BookingCreate, BookingResponse


router = APIRouter(
    prefix="/bookings",
    tags=["Bookings"],
)

PUBLIC_VERIFICATION_STATUSES = ("legacy", "verified")


@router.post("/", response_model=BookingResponse)
def create_booking(
    booking_data: BookingCreate,
    db: Session = Depends(get_db),
):
    hotel = db.query(Hotel).filter(
        Hotel.id == booking_data.hotel_id
    ).first()

    if hotel is None:
        raise HTTPException(status_code=404, detail="Hotel not found")

    if (
        hotel.verification_status not in PUBLIC_VERIFICATION_STATUSES
        or hotel.is_active is not True
        or hotel.available is not True
    ):
        raise HTTPException(
            status_code=409,
            detail="This hotel is not currently accepting bookings",
        )

    if booking_data.check_in is None or booking_data.check_out is None:
        raise HTTPException(
            status_code=422,
            detail="Check-in and check-out dates are required",
        )

    if booking_data.check_in < date.today():
        raise HTTPException(
            status_code=422,
            detail="Check-in date cannot be in the past",
        )

    if booking_data.check_out <= booking_data.check_in:
        raise HTTPException(
            status_code=422,
            detail="Check-out date must be after check-in date",
        )

    booking = Booking(
        hotel_id=booking_data.hotel_id,
        customer_name=booking_data.customer_name,
        customer_email=booking_data.customer_email,
        check_in=booking_data.check_in,
        check_out=booking_data.check_out,
        status="pending",
    )

    try:
        db.add(booking)
        db.commit()
        db.refresh(booking)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Unable to save booking")

    return booking
