from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models import City, Hotel
from routers.transport import get_current_admin
from schemas import HotelResponse

router = APIRouter(prefix="/hotels", tags=["Hotels"])


def public_hotels(db: Session):
    # 'legacy' preserves earlier public listings without claiming SLTDA verification.
    return db.query(Hotel).filter(
        Hotel.available.is_(True),
        Hotel.is_active.is_(True),
        Hotel.verification_status.in_(["legacy", "verified"]),
    )


class HotelFields(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    address: str | None = None
    description: str | None = None
    district: str = Field(min_length=2, max_length=100)
    accommodation_type: str | None = None
    registration_no: str = Field(min_length=3, max_length=100)
    licence_no: str | None = None
    price_per_night: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    city_id: int | None = Field(default=None, gt=0)
    latitude: float | None = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    longitude: float | None = Field(default=None, ge=-180, le=180, allow_inf_nan=False)

    @field_validator("name", "district", "registration_no")
    @classmethod
    def strip_required(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Value is too short")
        return value


class AdminHotelCreate(HotelFields):
    pass


class AdminHotelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    address: str | None = None
    description: str | None = None
    district: str | None = Field(default=None, min_length=2, max_length=100)
    accommodation_type: str | None = None
    registration_no: str | None = Field(default=None, min_length=3, max_length=100)
    licence_no: str | None = None
    price_per_night: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    city_id: int | None = Field(default=None, gt=0)
    latitude: float | None = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    longitude: float | None = Field(default=None, ge=-180, le=180, allow_inf_nan=False)
    available: bool | None = None


class VerificationChange(BaseModel):
    verification_status: Literal["pending", "verified", "rejected"]
    # An explicit confirmation is required; this is NOT an SLTDA API check.
    evidence_checked: bool = False


class ActivationChange(BaseModel):
    is_active: bool


def check_hotel_fields(db: Session, values: dict, hotel_id: int | None = None):
    reg = values.get("registration_no")
    if reg is not None:
        reg = reg.strip()
        if len(reg) < 3:
            raise HTTPException(422, "Invalid registration number")
        duplicate = db.query(Hotel).filter(
            func.lower(func.trim(Hotel.registration_no)) == reg.lower()
        )
        if hotel_id is not None:
            duplicate = duplicate.filter(Hotel.id != hotel_id)
        if duplicate.first():
            raise HTTPException(409, "Hotel registration number already exists")
        values["registration_no"] = reg

    if values.get("name") is not None:
        values["name"] = values["name"].strip()
        if len(values["name"]) < 2:
            raise HTTPException(422, "Invalid hotel name")
    if values.get("district") is not None:
        values["district"] = values["district"].strip()
        if len(values["district"]) < 2:
            raise HTTPException(422, "Invalid district")

    if hotel_id is not None:
        original = db.query(Hotel).filter(Hotel.id == hotel_id).first()
        if not original:
            raise HTTPException(404, "Hotel not found")
        city_id = values.get("city_id", original.city_id)
        district = values.get("district", original.district)
        lat = values.get("latitude", original.latitude)
        lon = values.get("longitude", original.longitude)
    else:
        city_id = values.get("city_id")
        district = values.get("district")
        lat = values.get("latitude")
        lon = values.get("longitude")

    if (lat is None) != (lon is None):
        raise HTTPException(422, "Latitude and longitude must be provided together")
    if city_id is not None:
        city = db.query(City).filter(City.id == city_id).first()
        if not city:
            raise HTTPException(404, "City not found")
        if city.district and city.district.strip().casefold() != district.casefold():
            raise HTTPException(422, "City does not belong to the selected district")
    return values


def admin_hotel_dict(hotel: Hotel):
    return {
        "id": hotel.id, "name": hotel.name, "address": hotel.address,
        "description": hotel.description, "district": hotel.district,
        "accommodation_type": hotel.accommodation_type,
        "registration_no": hotel.registration_no, "licence_no": hotel.licence_no,
        "source": hotel.source, "price_per_night": hotel.price_per_night,
        "rating": hotel.rating, "available": hotel.available,
        "city_id": hotel.city_id, "latitude": hotel.latitude,
        "longitude": hotel.longitude,
        "verification_status": hotel.verification_status,
        "is_active": hotel.is_active,
    }


@router.get("/", response_model=list[HotelResponse])
def get_all_hotels(db: Session = Depends(get_db)):
    return public_hotels(db).all()


@router.get("/city/{city_name}", response_model=list[HotelResponse])
def get_hotels_by_city(city_name: str, db: Session = Depends(get_db)):
    city = db.query(City).filter(City.name.ilike(city_name)).first()
    if not city:
        raise HTTPException(404, "City not found")
    return public_hotels(db).filter(Hotel.city_id == city.id).all()


@router.get("/district/{district_name}", response_model=list[HotelResponse])
def get_hotels_by_district(district_name: str, db: Session = Depends(get_db)):
    hotels = public_hotels(db).filter(Hotel.district.ilike(district_name)).all()
    if not hotels:
        raise HTTPException(404, "District not found or no public hotels")
    return hotels


@router.get("/admin/list")
def admin_list_hotels(db: Session = Depends(get_db), admin: dict = Depends(get_current_admin)):
    return [admin_hotel_dict(h) for h in db.query(Hotel).order_by(Hotel.id.desc()).all()]


@router.post("/admin", status_code=status.HTTP_201_CREATED)
def add_hotel_by_admin(
    hotel_data: AdminHotelCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    values = check_hotel_fields(db, hotel_data.model_dump())
    hotel = Hotel(
        **values,
        source="Admin submitted - verification pending",
        verification_status="pending",
        is_active=False,
        available=False,
    )
    try:
        db.add(hotel)
        db.commit()
        db.refresh(hotel)
    except Exception:
        db.rollback()
        raise HTTPException(500, "Failed to save hotel")
    return {"message": "Hotel saved; manual verification required", "hotel": admin_hotel_dict(hotel)}


@router.patch("/admin/{hotel_id}")
def admin_update_hotel(
    hotel_id: int,
    changes: AdminHotelUpdate,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(404, "Hotel not found")
    values = check_hotel_fields(db, changes.model_dump(exclude_unset=True), hotel_id)
    for key, value in values.items():
        setattr(hotel, key, value)
    try:
        db.commit()
        db.refresh(hotel)
    except Exception:
        db.rollback()
        raise HTTPException(500, "Failed to update hotel")
    return admin_hotel_dict(hotel)


@router.patch("/admin/{hotel_id}/verification")
def admin_verify_hotel(
    hotel_id: int,
    change: VerificationChange,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(404, "Hotel not found")
    if change.verification_status == "verified" and not change.evidence_checked:
        raise HTTPException(422, "Confirm official registration evidence was manually checked")
    hotel.verification_status = change.verification_status
    if change.verification_status != "verified":
        hotel.is_active = False
    try:
        db.commit()
        db.refresh(hotel)
    except Exception:
        db.rollback()
        raise HTTPException(500, "Failed to update verification")
    return admin_hotel_dict(hotel)


@router.patch("/admin/{hotel_id}/activation")
def admin_activate_hotel(
    hotel_id: int,
    change: ActivationChange,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    hotel = db.query(Hotel).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(404, "Hotel not found")
    if change.is_active and hotel.verification_status not in ("legacy", "verified"):
        raise HTTPException(409, "Only legacy or verified hotels can be activated")
    hotel.is_active = change.is_active
    try:
        db.commit()
        db.refresh(hotel)
    except Exception:
        db.rollback()
        raise HTTPException(500, "Failed to update activation")
    return admin_hotel_dict(hotel)


@router.get("/{hotel_id}", response_model=HotelResponse)
def get_hotel(hotel_id: int, db: Session = Depends(get_db)):
    hotel = public_hotels(db).filter(Hotel.id == hotel_id).first()
    if not hotel:
        raise HTTPException(404, "Hotel not found or not publicly available")
    return hotel

