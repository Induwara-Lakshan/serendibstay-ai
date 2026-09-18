from datetime import date
from pydantic import BaseModel


class HotelResponse(BaseModel):
    id: int
    name: str
    address: str | None = None
    description: str | None = None

    district: str
    accommodation_type: str | None = None
    registration_no: str | None = None
    licence_no: str | None = None
    source: str | None = None

    price_per_night: float | None = None
    rating: float | None = None
    available: bool | None = None
    city_id: int | None = None

    class Config:
        from_attributes = True


class BookingCreate(BaseModel):
    hotel_id: int
    customer_name: str
    customer_email: str
    check_in: date
    check_out: date
    status: str = "confirmed"


class BookingResponse(BookingCreate):
    id: int

    class Config:
        from_attributes = True