'''
----------------------------
Project actions
USER INTERACTIONS
----------------------------
'''

from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from db import db
from models import ProjectModel 
from schemas import ProjectSchema, PlainProjectSchema, ProjectUpdateSchema

# Define the Blueprint for projects
blp = Blueprint("projects", __name__, description = "Operations on projects")


# Endpoint for generic create and view projects
@blp.route("/projects")
# Handles getting project data, and creating projects
class ProjectListAndCreate(MethodView):
    @jwt_required()
    @blp.arguments(PlainProjectSchema)  
    @blp.response(201, ProjectSchema)   
    def post(self, project_data):
        # Create a new project for the authenticated user
        current_user_id = get_jwt_identity()
        
        project = ProjectModel(user_id = current_user_id, **project_data)
        
        try:
            db.session.add(project)
            db.session.commit()
        # Handles issues like non-unique names
        except IntegrityError: 
            db.session.rollback()
            # This specific IntegrityError might be less likely now that ProjectModel.name is not unique=True
            # but good to keep for other potential integrity issues.
            abort(400, message = f"Database integrity error") 
        except SQLAlchemyError:
            db.session.rollback()
            abort(500, message = f"An error occurred while creating the project")
            
        return project
    
    # User login required -- easy check for their own projects
    @jwt_required() 
    # Can return many projects
    @blp.response(200, ProjectSchema(many=True))
    def get(self):
        # Get all projects for the authenticated user
        current_user_id = get_jwt_identity()
        
        try:
            # Query projects belonging to the current user
            projects = ProjectModel.query.filter_by(user_id=current_user_id).all()
            return projects
        except:
            abort(500, message = "Error, a problem occured retrieving projects")

# Endpoint related to a specific project
@blp.route("/projects/<int:project_id>")
class ProjectResource(MethodView):
    @jwt_required()
    @blp.response(200, ProjectSchema)
    # Get specific project by the project ID
    def get(self, project_id):
        current_user_id = get_jwt_identity()
        # Get project, ensuring it belongs to user
        try:
            project = ProjectModel.query.filter_by(id = project_id, user_id = current_user_id).first_or_404()
            return project
        except SQLAlchemyError:
            abort(500, message = "Error, a problem occured retrieving projects")
    
    # Updating project name + description
    @jwt_required()
    @blp.arguments(ProjectUpdateSchema)
    @blp.response(200, ProjectSchema)
    # Patch reflects partial update
    def patch(self, project_data, project_id):
        current_user_id = get_jwt_identity()
        project = ProjectModel.query.filter_by(id=project_id, user_id=current_user_id).first_or_404()

        # Update fields part of project_data
        if "name" in project_data:
            project.name = project_data["name"]
        if "description" in project_data:
            project.description = project_data["description"]

        try:
            db.session.add(project)
            db.session.commit()

        except IntegrityError:
            db.session.rollback()
            abort(400, message = f"Database integrity error")
        except SQLAlchemyError:
            db.session.rollback()
            abort(500, message = f"An error occurred while updating the project")
            
    @jwt_required()
    def delete(self, project_id):
        # Delete a project
        current_user_id = get_jwt_identity()
        project = ProjectModel.query.filter_by(id=project_id, user_id=current_user_id).first_or_404()
        
        try:
            db.session.delete(project)
            db.session.commit()
        except SQLAlchemyError as e:
            db.session.rollback()
            abort(500, message = f"An error occurred while deleting the project: {str(e.orig)}")
            
        return {"message": "Project deleted successfully"}
    

# This route is dedicated for public access / feed page
# No JWTS / login should be needed to access this
@blp.route("/projects/public")
class PublicProjectList(MethodView):
    # Returns many projects
    @blp.response(200, ProjectSchema(many=True))
    def get(self):
        # Get a list of all publicly available projects
        # ***NOTE: For now, all projects are public
        try:
            # ***NOTE: Order by newest for now
            projects = ProjectModel.query.order_by(ProjectModel.id.desc()).all() 
            return projects
        except SQLAlchemyError:
            abort(500, message="An error occurred while retrieving public projects.")
