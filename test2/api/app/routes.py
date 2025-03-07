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

# User CRUD Operations
@app.route("/api/users", methods=["GET"])
async def get_users(req, res):
    """Get all users"""
    users = db.query("SELECT * FROM users")
    return await res.json({"users": users})

@app.route("/api/users/{id}", methods=["GET"])
async def get_user(req, res):
    """Get a single user"""
    user = db.get_one("SELECT * FROM users WHERE id = ?", (req.path_params['id'],))
    if not user:
        return await res.json({"error": "User not found"}, status=404)
    return await res.json({"user": user})

@app.route("/api/users", methods=["POST"])
async def create_user(req, res):
    """Create one or multiple users"""
    try:
        data = await req.json()
        
        # Handle both single and bulk creation
        if isinstance(data, list):
            # Bulk creation
            for item in data:
                if not all(k in item for k in ('name', 'email')):
                    return await res.json({
                        "error": "Each user must have name and email"
                    }, status=400)
            
            user_ids = db.insert('users', data)
            return await res.json({
                "message": f"{len(data)} users created successfully",
                "users": data
            }, status=201)
        else:
            # Single creation
            if not all(k in data for k in ('name', 'email')):
                return await res.json({
                    "error": "Missing required fields: name, email"
                }, status=400)
            
            user_id = db.insert('users', data)
            data['id'] = user_id
            return await res.json({
                "message": "User created successfully",
                "user": data
            }, status=201)
    except Exception as e:
        return await res.json({
            "error": str(e)
        }, status=400)

@app.route("/api/users/{id}", methods=["PUT"])
async def update_user(req, res):
    """Update a user"""
    try:
        data = await req.json()
        user_id = req.path_params['id']
        
        # Check if user exists
        if not db.get_one("SELECT 1 FROM users WHERE id = ?", (user_id,)):
            return await res.json({"error": "User not found"}, status=404)
        
        rows_affected = db.update(
            'users',
            data,
            "id = ?",
            (user_id,)
        )
        
        return await res.json({
            "message": "User updated successfully",
            "user": {**data, "id": user_id}
        })
    except Exception as e:
        return await res.json({"error": str(e)}, status=400)

@app.route("/api/users/{id}", methods=["DELETE"])
async def delete_user(req, res):
    """Delete a user"""
    user_id = req.path_params['id']
    
    # Check if user exists
    if not db.get_one("SELECT 1 FROM users WHERE id = ?", (user_id,)):
        return await res.json({"error": "User not found"}, status=404)
    
    db.delete('users', "id = ?", (user_id,))
    return await res.json({
        "message": "User deleted successfully"
    })

# Add your routes here 