from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Booking, Hotel
from schemas import BookingCreate, BookingResponse


router = APIRouter(
    prefix="/bookings",
    tags=["Bookings"]
)


@router.post("/", response_model=BookingResponse)
def create_booking(
    booking_data: BookingCreate,
    db: Session = Depends(get_db)
):

    hotel = db.query(Hotel).filter(
        Hotel.id == booking_data.hotel_id
    ).first()

    if not hotel:
        raise HTTPException(
            status_code=404,
            detail="Hotel not found"
        )

    booking = Booking(
        hotel_id=booking_data.hotel_id,
        customer_name=booking_data.customer_name,
        customer_email=booking_data.customer_email,
        check_in=booking_data.check_in,
        check_out=booking_data.check_out,
        status=booking_data.status
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)

    return booking