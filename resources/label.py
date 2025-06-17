'''
----------------------------
Label actions (and AI context creation indirectly)
USER INTERACTIONS
----------------------------
'''

from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from db import db
from models import ProjectModel, LabelModel, RefinedLabelModel
from schemas import ProjectAddLabelsSchema, LabelSchema
from marshmallow import fields

from resources.gemini import gemini_service_instance

blp = Blueprint("labels", __name__, description = "Operations on project labels")

@blp.route("/projects/<int:project_id>/labels")
class ProjectLabelsList(MethodView):
    @jwt_required()
    @blp.response(200, LabelSchema(many = True))
    # Return all input labels that user has entered for a project
    def get(self, project_id):
        # Initialize user and retrieve ID
        current_user_id = get_jwt_identity()

        # Find project by ID
        project = ProjectModel.query.filter_by(id = project_id, user_id = current_user_id).first_or_404(
            description = "Project not found or you do not have permission to access its labels."
        )

        return project.labels.all()
    
    @jwt_required()
    @blp.arguments(ProjectAddLabelsSchema)
    @blp.response(201, LabelSchema(many = True))
    def post(self, labels_data, project_id):
        # Find user
        current_user_id = get_jwt_identity()

        # Add 1-10 input labels
        project = ProjectModel.query.filter_by(id = project_id, user_id = current_user_id).first_or_404(
            description = "Project not found, or you do not have permission to add labels"
        )
        if (project.labels.count() + len(labels_data["labels"])) > 10:
            abort(400, message = "Adding these labels would exceed limit of labels 10 per project")

        # Will iterate and append to this list
        created_input_labels_for_response = []
        # Predefined difficulty options
        difficulties = ["simple", "intermediate", "in_depth"]


        try:
            for label_text in labels_data["labels"]:
                if not label_text.strip():
                    continue
                
                label = LabelModel(text=label_text, project_id=project.id)
                db.session.add(label)
                created_input_labels_for_response.append(label)

            # Flush session to get IDs for newly inputted labels
            db.session.flush()

            # Now generate 3 responses for each label (based on difficulty)

            for label_instance in created_input_labels_for_response:
                # Should have label ID by now
                if not label_instance.id:
                    print(f"Warning: Label not received, or failed to assign ID")
                    continue
            
                # Generate responses for each difficulty
                for difficulty in difficulties:
                    try:
                        """"
                        refine_label_text is a method inside gemini.py
                        which takes 2 input parameters:
                        (label_text, difficulty)
                        """
                        # Call the Gemini service
                        refined_text_content = gemini_service_instance.refine_label_text(
                            label_text = label_instance.text, 
                            difficulty = difficulty,
                            project_name = project.name,
                            project_description = project.description
                        )

                        # Data for the new RefinedLabelModel
                        refined_label_data_to_create = {
                            "generated_text": refined_text_content,
                            "difficulty": difficulty,
                            "input_label_id": label_instance.id
                        }

                        new_refined_label = RefinedLabelModel(
                            generated_text = refined_label_data_to_create["generated_text"], 
                            difficulty = refined_label_data_to_create["difficulty"],
                            # Link it to the current LabelModel 
                            input_label_id = label_instance.id
                        )
                        db.session.add(new_refined_label)

                    # Catch errors from GeminiService
                    except ConnectionError as e_gemini:
                        db.session.rollback()
                        abort(502, message = f"Error generating explanations '{label_instance.text}' (ID: {label_instance.id}) with difficulty '{difficulty}': {str(e_gemini)}")
                        
                    except Exception as e_other_refinement: # Catch any other unexpected error during refinement
                        db.session.rollback()
                        abort(500, message = f"Unexpected error during refinement of label ID {label_instance.id}, difficulty {difficulty}: {e_other_refinement}")
                        
                    
            db.session.commit()


        except IntegrityError:
            db.session.rollback()
            abort(400, message = f"Database integrity error while adding labels")
        except SQLAlchemyError:
            abort(500, message = f"An error occurred while adding labels")

        return created_input_labels_for_response
    
# Actions on specific labels
@blp.route("/labels/<int:label_id>")
class LabelResource(MethodView):
    @jwt_required()
    @blp.response(200, LabelSchema)
    def get(self, label_id):
        # Find linked labels by user ID
        current_user_id = get_jwt_identity()
        # Ensure the label exists and belongs to a project owned by the current user
        label = db.session.query(LabelModel).join(ProjectModel).filter(
            LabelModel.id == label_id,
            ProjectModel.user_id == current_user_id
        ).first_or_404(description="Label not found or access denied.")
        return label

    @jwt_required()
    def delete(self, label_id):
        # Delete a specific label (and its associated refined_label)
        current_user_id = get_jwt_identity()
        # Ensure the label exists to a project and its user
        label = db.session.query(LabelModel).join(ProjectModel).filter(
            LabelModel.id == label_id,
            ProjectModel.user_id == current_user_id
        ).first_or_404(description="Label not found or access denied")

        try:
            # Also deletes refined_label model due to cascade
            db.session.delete(label) 
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            abort(500, message=f"An error occurred while deleting the label")
                    
        return {"message": "Label deleted successfully"}
