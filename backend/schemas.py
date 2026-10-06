from datetime import date, time
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


class TransportProviderCreate(BaseModel):
    provider_name: str
    phone: str
    email: str
    password: str
    vehicle_type: str
    vehicle_number: str
    passenger_capacity: int
    base_district: str
    service_districts: list[str]

class TransportProviderLogin(BaseModel):
    email: str
    password: str

class TransportProviderResponse(BaseModel):
    id: int
    provider_name: str
    phone: str
    email: str

    vehicle_type: str
    vehicle_number: str
    passenger_capacity: int

    base_district: str
    service_districts: list[str] = []

    approved: bool
    available: bool

    class Config:
        from_attributes = True


class TransportRequestCreate(BaseModel):
    provider_id: int

    customer_name: str
    customer_email: str
    customer_phone: str

    pickup_location: str
    destination: str

    pickup_date: date
    pickup_time: time

    passengers: int


class TransportRequestResponse(TransportRequestCreate):
    id: int
    status: str

    class Config:
        from_attributes = True


