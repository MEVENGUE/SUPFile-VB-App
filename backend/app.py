"""
Entry point for running the application directly
"""
from app.main import app
import uvicorn
import os
from app.core.config import settings

if name == "main":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        reload=settings.DEBUG,
    )

