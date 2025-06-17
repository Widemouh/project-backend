from db import db

class LabelModel(db.Model):
    __tablename__ = "labels"

    id = db.Column(db.Integer, primary_key=True)
    # User text/label
    text = db.Column(db.String(100), nullable=False)

    # Corresponding project ID
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable = False)
    # Label-Project relationship
    project = db.relationship("ProjectModel", back_populates = "labels")
    # Relationship to generated response based on the user's label
    refinements = db.relationship(
        "RefinedLabelModel",
        back_populates = "input_label",
        cascade = "all, delete-orphan"
    )
