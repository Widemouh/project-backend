'''
----------------------------
User/account actions
USER INTERACTIONS
----------------------------
'''

from flask.views import MethodView
# Blueprint divides APIs into smaller segments
from flask_smorest import Blueprint, abort
# Hashes the password that the user enters
# and saves the scrambled password into the database
from passlib.hash import pbkdf2_sha256
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, get_jwt

from db import db
from schemas import UserSchema, PlainUserSchema
from models.tokens_blocklist import TokenBlocklist
from models import UserModel

blp = Blueprint("users", __name__, description = "Operations on users")

@blp.route("/register")
class UserRegister(MethodView):
    @blp.arguments(PlainUserSchema)
    def post(self, user_data):
        if UserModel.query.filter(UserModel.username == user_data["username"]).first():
            abort(409, message = "A user with that name already exists")

        user = UserModel(
            username = user_data["username"],
            password = pbkdf2_sha256.hash(user_data["password"])
        )
        db.session.add(user)
        db.session.commit()

        return {"message": "User created successfully."}, 201
    
@blp.route("/login")
class UserLogin(MethodView):
    @blp.arguments(PlainUserSchema)
    def post(self, user_data):
        user = UserModel.query.filter(
            UserModel.username == user_data["username"]
        ).first()
        
        # user must not be null, and verify must return True
        if user and pbkdf2_sha256.verify(user_data["password"], user.password):
            # Store short-lived access token
            access_token = create_access_token(identity = str(user.id))
            return {"access_token": access_token}
        
        abort(401, message = "Invalid credentials")


@blp.route("/logout")
class UserLogout(MethodView):
    @jwt_required()
    def post(self):
        # Can also use .get("jti")
        jti = get_jwt()["jti"]
        # This only stores locally, so this resets when restarting app
        # Use a database, such as storing in a table with SQL to improve this
        if not TokenBlocklist.query.filter_by(jti=jti).first():
            db.session.add(TokenBlocklist(jti=jti))
            db.session.commit()
        return {"message": "Logged out successfully"}

@blp.route("/user/<int:user_id>")
class User(MethodView):
    @blp.response(200, UserSchema)
    # Get user info
    def get(self, user_id):
        user = UserModel.query.get_or_404(user_id)
        return user
    
    # Delete user
    @jwt_required()
    def delete(self, user_id):
        current_user_id = get_jwt_identity()
        if current_user_id != str(user_id) and not get_jwt().get("is_admin"):
            abort(403, message = "You are not authorized to delete this user")
        user = UserModel.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return {"message": "User deleted"}
