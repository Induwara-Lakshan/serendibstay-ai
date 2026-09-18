from sqlalchemy import Column, Integer, String, Float, Boolean, Date, ForeignKey
from database import Base


class City(Base):
    __tablename__ = "cities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    district = Column(String)
    province = Column(String)


class Hotel(Base):
    __tablename__ = "hotels"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String)
    description = Column(String)

    district = Column(String, nullable=False)
    accommodation_type = Column(String)

    registration_no = Column(String)
    licence_no = Column(String)
    source = Column(String, default="Sri Lanka Tourism")

    price_per_night = Column(Float, nullable=True)
    rating = Column(Float, nullable=True)
    available = Column(Boolean, default=True)

    city_id = Column(Integer, ForeignKey("cities.id"))


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"))
    customer_name = Column(String, nullable=False)
    customer_email = Column(String, nullable=False)
    check_in = Column(Date)
    check_out = Column(Date)
    status = Column(String)