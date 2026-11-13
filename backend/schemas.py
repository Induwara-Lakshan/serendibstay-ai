from datetime import date, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


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
    latitude: float | None = None
    longitude: float | None = None

    model_config = ConfigDict(from_attributes=True)


class BookingCreate(BaseModel):
    hotel_id: int = Field(gt=0)
    customer_name: str = Field(min_length=1)
    customer_email: str
    check_in: date
    check_out: date
    status: Literal["pending"] = "pending"

    @model_validator(mode="after")
    def validate_dates(self):
        if self.check_in < date.today():
            raise ValueError("Check-in date cannot be in the past")
        if self.check_out <= self.check_in:
            raise ValueError("Check-out date must be after check-in date")
        return self


class BookingResponse(BaseModel):
    id: int
    hotel_id: int
    customer_name: str
    customer_email: str
    check_in: date
    check_out: date
    status: str

    model_config = ConfigDict(from_attributes=True)


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
    service_districts: list[str] = Field(default_factory=list)
    approved: bool
    available: bool

    model_config = ConfigDict(from_attributes=True)


class TransportRequestCreate(BaseModel):
    provider_id: int
    customer_name: str
    customer_email: EmailStr
    customer_phone: str
    pickup_location: str
    destination: str
    pickup_date: date
    pickup_time: time
    passengers: int


class TransportRequestResponse(TransportRequestCreate):
    id: int
    status: str

    model_config = ConfigDict(from_attributes=True)
