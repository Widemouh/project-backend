from db import db

class UserModel(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key = True)
    # Unique username
    username = db.Column(db.String(80), unique = True, nullable = False)
    # Make sure password isn't unique, or else people will know someone has that password
    password = db.Column(db.String(256), nullable = False)

    # One user can have many projects
    # Projects delete if account is deleted
    projects = db.relationship("ProjectModel", back_populates = "user", lazy = "dynamic", cascade="all, delete-orphan")
