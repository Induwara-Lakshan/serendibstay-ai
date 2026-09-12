from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Hotel
from schemas import HotelResponse


router = APIRouter(
    prefix="/hotels",
    tags=["Hotels"]
)


@router.get("/", response_model=list[HotelResponse])
def get_all_hotels(db: Session = Depends(get_db)):
    return db.query(Hotel).all()


@router.get("/{hotel_id}", response_model=HotelResponse)
def get_hotel(hotel_id: int, db: Session = Depends(get_db)):

    hotel = db.query(Hotel).filter(
        Hotel.id == hotel_id
    ).first()

    if not hotel:
        raise HTTPException(
            status_code=404,
            detail="Hotel not found"
        )

    return hotel


@router.get("/city/{city_name}", response_model=list[HotelResponse])
def get_hotels_by_city(
    city_name: str,
    db: Session = Depends(get_db)
):

    from models import City

    city = db.query(City).filter(
        City.name.ilike(city_name)
    ).first()

    if not city:
        raise HTTPException(
            status_code=404,
            detail="City not found"
        )

    hotels = db.query(Hotel).filter(
        Hotel.city_id == city.id
    ).all()

    return hotels