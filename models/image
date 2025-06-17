from db import db

class ImageModel(db.Model):
    __tablename__ = "images"

    id = db.Column(db.Integer, primary_key=True)
    # Store the file name just in case
    filename = db.Column(db.String(255), nullable=False) 
    # Full path to the image file in your Google Cloud Storage bucket -- Must be unique
    gcs_path = db.Column(db.String(1024), nullable=False, unique=True) 
    # Type of image (JPEG will be used for low storage usage)
    content_type = db.Column(db.String(80), nullable=False)

    # Foreign Key to link to the Project model
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    # Relationship back to ProjectModel
    # Each ImageModel instance belongs to one ProjectModel
    project = db.relationship("ProjectModel", back_populates="images")
