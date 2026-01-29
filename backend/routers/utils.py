from fastapi import APIRouter

router = APIRouter(tags=["utils"])


@router.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Food Scanner API is running"}

