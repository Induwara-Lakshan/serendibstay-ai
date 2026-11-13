"""Isolated booking API tests; never connects to the project's PostgreSQL DB.

Run inside the backend environment:
    python -m unittest discover -s tests -p 'test_booking_restrictions.py' -v
"""
import unittest
from datetime import date, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from models import Hotel
from routers.bookings import router as bookings_router


class BookingRestrictionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self.app = FastAPI()
        self.app.include_router(bookings_router)

        def override_get_db():
            session = self.Session()
            try:
                yield session
            finally:
                session.close()

        self.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        self.app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def add_hotel(self, *, verification_status="legacy", is_active=True, available=True):
        with self.Session() as session:
            hotel = Hotel(
                name="Automated Test Hotel",
                district="Kandy",
                verification_status=verification_status,
                is_active=is_active,
                available=available,
            )
            session.add(hotel)
            session.commit()
            session.refresh(hotel)
            return hotel.id

    def booking_payload(self, hotel_id):
        check_in = date.today() + timedelta(days=30)
        return {
            "hotel_id": hotel_id,
            "customer_name": "Test Guest",
            "customer_email": "test@example.com",
            "check_in": check_in.isoformat(),
            "check_out": (check_in + timedelta(days=2)).isoformat(),
            "status": "pending",
        }

    def assert_blocked(self, **hotel_settings):
        hotel_id = self.add_hotel(**hotel_settings)
        response = self.client.post("/bookings/", json=self.booking_payload(hotel_id))
        self.assertEqual(response.status_code, 409, response.text)

    def test_pending_hotel_blocked(self):
        self.assert_blocked(verification_status="pending", is_active=False)

    def test_rejected_hotel_blocked(self):
        self.assert_blocked(verification_status="rejected")

    def test_inactive_hotel_blocked(self):
        self.assert_blocked(is_active=False)

    def test_unavailable_hotel_blocked(self):
        self.assert_blocked(available=False)

    def test_missing_hotel_returns_404(self):
        response = self.client.post("/bookings/", json=self.booking_payload(999999))
        self.assertEqual(response.status_code, 404, response.text)

    def test_valid_legacy_hotel_booking_is_pending(self):
        hotel_id = self.add_hotel()
        response = self.client.post("/bookings/", json=self.booking_payload(hotel_id))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "pending")

    def test_valid_verified_hotel_booking_is_pending(self):
        hotel_id = self.add_hotel(verification_status="verified")
        response = self.client.post("/bookings/", json=self.booking_payload(hotel_id))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "pending")


if __name__ == "__main__":
    unittest.main()
