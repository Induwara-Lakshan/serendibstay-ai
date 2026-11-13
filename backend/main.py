from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from routers.payhere import router as payhere_router

from routers.hotels import router as hotels_router
from routers.bookings import router as bookings_router
from routers.chat import router as chat_router
from routers.transport import router as transport_router
from routers.transport_routes import router as transport_routes_router

from routers.directions import router as directions_router

app = FastAPI(
    title="Sri Lanka Hotel API",  
    description="REST API for searching and booking hotels in Sri Lanka",
    version="1.0.0"
)

# Allow React frontend to communicate with FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
    "http://localhost:5184",
    "http://127.0.0.1:5184",
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hotels_router)
app.include_router(bookings_router)
app.include_router(chat_router)
app.include_router(transport_router)
app.include_router(transport_routes_router)

app.include_router(directions_router)

app.include_router(payhere_router)


@app.get("/")
def root():
    return {
        "message": "Sri Lanka Hotel API is running"
    }