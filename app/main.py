"""
FastAPI application entry point.
Refactored to follow Clean Code principles using ApplicationBuilder.
"""

from app.core.application import create_application

# Create the FastAPI application using the builder pattern
app = create_application()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
