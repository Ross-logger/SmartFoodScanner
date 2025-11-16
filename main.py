from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth, users, scans, history, dietary, utils
import uvicorn

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="Smart Food Scanner API",
    description="Backend API for food ingredient scanning and dietary analysis",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with /api prefix
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(scans.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(dietary.router, prefix="/api")
app.include_router(utils.router, prefix="/api")


@app.get("/")
def root():
    """Root endpoint"""
    return {
        "message": "Smart Food Scanner API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)