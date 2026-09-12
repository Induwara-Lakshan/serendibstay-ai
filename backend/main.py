from fastapi import FastAPI

from routers.hotels import router as hotels_router
from routers.bookings import router as bookings_router


app = FastAPI(
    title="Sri Lanka Hotel API",
    description="REST API for searching and booking hotels in Sri Lanka",
    version="1.0.0"
)


app.include_router(hotels_router)
app.include_router(bookings_router)


@app.get("/")
def root():
    return {
        "message": "Sri Lanka Hotel API is running"
    }