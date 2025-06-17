from db import db

class ProjectModel(db.Model):
    __tablename__ = "projects"

    # Project id
    id = db.Column(db.Integer, primary_key = True)
    # Project name
    name = db.Column(db.String(120), unique = False, nullable = False)
    description = db.Column(db.Text, nullable = False)
    # User ID containing their projects
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable = False)
    # User-project relationship
    user = db.relationship("UserModel", back_populates = "projects")
    # InputLabel-project relationship, which also contains its Gemini repsonses
    labels = db.relationship("LabelModel", back_populates = "project", lazy = "dynamic", cascade = "all, delete-orphan")
    # Input images from user
    images = db.relationship("ImageModel", back_populates = "project", lazy = "dynamic", cascade = "all, delete-orphan")
