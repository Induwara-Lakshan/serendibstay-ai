
from sqlalchemy import Column, Integer, BigInteger, String, Float, Boolean, Date, Time, DateTime, Numeric, ForeignKey

from database import Base


from sqlalchemy.sql import func


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
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Separate administrative status from hotel availability.
    # 'legacy' means previously listed, NOT officially verified.
    verification_status = Column(
        String, nullable=False, default="pending", server_default="pending"
    )
    is_active = Column(
        Boolean, nullable=False, default=False, server_default="false"
    )


class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    hotel_id = Column(Integer, ForeignKey("hotels.id"))
    customer_name = Column(String, nullable=False)
    customer_email = Column(String, nullable=False)
    check_in = Column(Date)
    check_out = Column(Date)
    status = Column(String)


class TransportProvider(Base):
    __tablename__ = "transport_providers"
    id = Column(Integer, primary_key=True, index=True)
    provider_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, nullable=False)
    password_hash = Column(String, nullable=True)
    vehicle_type = Column(String, nullable=False)
    vehicle_number = Column(String, nullable=False)
    passenger_capacity = Column(Integer, nullable=False)
    base_district = Column(String, nullable=False)
    approved = Column(Boolean, default=False)
    available = Column(Boolean, default=True)


class ProviderServiceDistrict(Base):
    __tablename__ = "provider_service_districts"
    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("transport_providers.id"), nullable=False)
    district = Column(String, nullable=False)


class TransportRequest(Base):
    __tablename__ = "transport_requests"
    id = Column(Integer, primary_key=True, index=True)
    response_token = Column(String, nullable=True, unique=True)
    provider_id = Column(Integer, ForeignKey("transport_providers.id"), nullable=False)
    customer_name = Column(String, nullable=False)
    customer_email = Column(String, nullable=False)
    customer_phone = Column(String, nullable=False)
    pickup_location = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    pickup_date = Column(Date, nullable=False)
    pickup_time = Column(Time, nullable=False)
    passengers = Column(Integer, nullable=False)
    status = Column(String, default="pending")



class Payment(Base):
    __tablename__ = "payments"

    id = Column(BigInteger, primary_key=True, index=True)

    booking_id = Column(
        Integer,
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=False
    )

    order_id = Column(String(100), nullable=False, unique=True)

    provider = Column(String(30), nullable=False, default="payhere")

    amount = Column(Numeric(12, 2), nullable=False)

    currency = Column(String(3), nullable=False, default="LKR")

    status = Column(String(30), nullable=False, default="pending")

    payhere_payment_id = Column(
        String(100),
        unique=True,
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )


