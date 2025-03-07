from . import app
from .models import User, Product
import logging

logger = logging.getLogger(__name__)

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
        "timestamp": str(app.orm.cursor.execute("SELECT datetime('now')").fetchone()[0])
    })

# User CRUD Operations
@app.route("/api/users", methods=["GET"])
async def get_users(req, res):
    """Get all users"""
    try:
        users = User.objects().all()
        return await res.json({"users": [user.to_dict() for user in users]})
    except Exception as e:
        return await res.json({"error": str(e)}, status=500)

@app.route("/api/users/{id}", methods=["GET"])
async def get_user(req, res):
    """Get a single user"""
    try:
        user = User.objects().filter(id=req.path_params['id']).first()
        if not user:
            return await res.json({"error": "User not found"}, status=404)
        return await res.json({"user": user.to_dict()})
    except Exception as e:
        return await res.json({"error": str(e)}, status=500)

@app.route("/api/users", methods=["POST"])
async def create_user(req, res):
    """Create one or multiple users"""
    try:
        data = await req.json()
        
        if isinstance(data, list):
            # Bulk creation
            users = []
            for item in data:
                if not all(k in item for k in ('name', 'email')):
                    return await res.json({
                        "error": "Each user must have name and email"
                    }, status=400)
                try:
                    # Remove id if it's None
                    if 'id' in item and item['id'] is None:
                        del item['id']
                    user = User(**item)
                    user.save()
                    users.append(user)
                except Exception as e:
                    logger.error(f"Error creating user: {str(e)}")
                    return await res.json({
                        "error": str(e)
                    }, status=400)
            
            return await res.json({
                "message": f"{len(users)} users created successfully",
                "users": [user.to_dict() for user in users]
            }, status=201)
        else:
            # Single creation
            if not all(k in data for k in ('name', 'email')):
                return await res.json({
                    "error": "Missing required fields: name, email"
                }, status=400)
            
            try:
                # Remove id if it's None
                if 'id' in data and data['id'] is None:
                    del data['id']
                user = User(**data)
                user.save()
                
                return await res.json({
                    "message": "User created successfully",
                    "user": user.to_dict()
                }, status=201)
            except Exception as e:
                logger.error(f"Error creating user: {str(e)}")
                return await res.json({
                    "error": str(e)
                }, status=400)
    except Exception as e:
        logger.error(f"Create user error: {str(e)}")
        return await res.json({
            "error": str(e)
        }, status=400)

@app.route("/api/users/{id}", methods=["PUT"])
async def update_user(req, res):
    """Update a user"""
    try:
        data = await req.json()
        user_id = req.path_params.get('id')
        if not user_id:
            return await res.json({"error": "User ID is required"}, status=400)

        user = User.objects().filter(id=user_id).first()
        
        if not user:
            return await res.json({"error": "User not found"}, status=404)
        
        # Validate email uniqueness if it's being updated
        if 'email' in data and data['email'] != user.email:
            existing = User.objects().filter(email=data['email']).first()
            if existing:
                return await res.json({
                    "error": "Email already exists"
                }, status=400)

        # Update only allowed fields
        allowed_fields = {'name', 'email'}
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not update_data:
            return await res.json({"error": "No valid fields to update"}, status=400)
        
        for key, value in update_data.items():
            setattr(user, key, value)
        
        user.save()
        return await res.json({
            "message": "User updated successfully",
            "user": user.to_dict()
        })
    except Exception as e:
        logger.error(f"Update user error: {str(e)}")
        return await res.json({"error": str(e)}, status=400)

@app.route("/api/users/{id}", methods=["DELETE"])
async def delete_user(req, res):
    """Delete a user"""
    try:
        user_id = req.path_params.get('id')
        if not user_id:
            return await res.json({"error": "User ID is required"}, status=400)

        user = User.objects().filter(id=user_id).first()
        
        if not user:
            return await res.json({"error": "User not found"}, status=404)
        
        user.delete()
        return await res.json({
            "message": "User deleted successfully",
            "id": user_id
        })
    except Exception as e:
        logger.error(f"Delete user error: {str(e)}")
        return await res.json({"error": str(e)}, status=400)

# Add your routes here 