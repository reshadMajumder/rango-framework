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

@app.route("/api/users", methods=["POST"])
async def create_user(req, res):
    """Create a new user"""
    try:
        data = await req.json()
        db.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            (data['name'], data['email'])
        )
        return await res.json({
            "message": "User created successfully",
            "user": data
        }, status=201)
    except KeyError:
        return await res.json({
            "error": "Missing required fields: name, email"
        }, status=400)

# Add your routes here 
@app.route("/api/users", methods=["GET"])
async def get_users(req, res):
    """Get all users"""
    users = db.execute("SELECT * FROM users").fetchall()
    return await res.json({
        "users": users
    })