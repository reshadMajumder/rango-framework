from . import app
from .models import db

@app.route("/")
async def index(req, res):
    """
    Main index route
    req: SimpleRequest object
    res: SimpleResponse class
    """
    return await res.json({
        "message": "Welcome to Rango!",
        "docs": "https://rango-framework.readthedocs.io"
    })

@app.route("/api/health")
async def health_check(req, res):
    """Health check endpoint"""
    return await res.json({
        "status": "healthy",
        "database": "connected" if db.is_connected() else "disconnected",
        "timestamp": str(db.cursor.execute("SELECT datetime('now')").fetchone()[0])
    })

# Add your routes here 