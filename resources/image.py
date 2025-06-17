'''
----------------------------
Image actions (JPG and JPEG only)
USER INTERACTION
----------------------------
'''

import uuid
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename
from flask import current_app, request

from db import db
from models import ProjectModel, ImageModel
from schemas import PlainImageSchema

from google.cloud import storage

# Allowed image file types
ALLOWED_EXTENSIONS =  {'jpg', 'jpeg'}

blp = Blueprint("images", __name__, description = "Operations on project images")

# Uploads a file object to the GCS bucket and returns the GCS path
# Takes parameters file, file name, and file type
def _upload_file_to_gcs(file_to_upload, original_filename, content_type):
    bucket_name = current_app.config["GCS_BUCKET_NAME"]
    if not bucket_name:
        abort(500, message = "GCS bucket name is not configured")

    # Secure file name and retrieve extension
    safe_original_filename = secure_filename(original_filename)
    extension = ""
    if '.' in safe_original_filename:
        # Split list starting from the right, only dividing into 2 parts
        extension = safe_original_filename.rsplit('.', 1)[1].lower()
    
    # Create a unique blob name to avoid overwrites
    blob_name = f"project_images/{uuid.uuid4().hex}_{safe_original_filename}"

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        blob.upload_from_file(
            # From request.files
            file_to_upload, 
            content_type = content_type
        )
        # Return full GCS path to image blob
        return f"gs://{bucket_name}/{blob_name}"
    except Exception as e:
        # Log the GCS upload error
        print(f"GCS Upload Error: {e}")
        # Re-raise a more generic error or a custom one to be caught by the endpoint
        raise ConnectionError(f"Failed to upload image to cloud storage: {str(e)}")


def _delete_file_from_gcs(gcs_path):
    # Deletes a file from GCS given its full gs:// path.
    bucket_name = current_app.config["GCS_BUCKET_NAME"]
    if not bucket_name or not gcs_path.startswith(f"gs://{bucket_name}/"):
        print(f"Invalid GCS path or bucket name for deletion: {gcs_path}")
        return False

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob_name = gcs_path.replace(f"gs://{bucket_name}/", "", 1) # Extract blob name
        blob = bucket.blob(blob_name)
        blob.delete()
        print(f"Successfully deleted {blob_name} from GCS bucket {bucket_name}.")
        return True
    except Exception as e:
        print(f"GCS Delete Error for blob {blob_name}: {e}")
        # Depending on policy, you might want to raise an error or just log and return False
        return False

# --- API endpoints ---

@blp.route("/projects/<int:project_id>/images")
class ProjectImageUpload(MethodView):
    @jwt_required()
    @blp.response(201, PlainImageSchema)
    def post(self, project_id):
        current_user_id = get_jwt_identity()
        
        project = ProjectModel.query.filter_by(id = project_id, user_id = current_user_id).first_or_404(
            description = "Project not found or permission denied"
        )

        if project.images.count() >= 3:
            abort(400, message = "Maximum of 3 images already uploaded for this project")

        if "image" not in request.files:
            abort(400, message = "No image file part in the request")

        file = request.files["image"]

        if file.filename == '':
            abort(400, message = "No image file selected")

        # Validate file extension (JPEG or JPG)
        if file:
            original_filename = secure_filename(file.filename)
            file_extension = ''
            if '.' in original_filename:
                file_extension = original_filename.rsplit('.', 1)[1].lower()

            # Validate file extension (JPEG or JPG)
            if file_extension not in ALLOWED_EXTENSIONS:
                abort(400, message = f"File type not allowed. Please upload one of: {', '.join(ALLOWED_EXTENSIONS)}")

            # Upload to GCS
            try:
                # From user input, defined in earlier function
                gcs_path = _upload_file_to_gcs(
                    file_to_upload = file,
                    original_filename = original_filename,
                    content_type = file.content_type
                )
            except ConnectionError as e:
                abort(500, message = str(e))
            except Exception as e:
                print(f"Unexpected GCS upload error: {e}")
                abort(500, message = "An error occurred during image upload")

            # Create ImageModel instance (contains metadata)
            image_metadata = ImageModel(
                filename = original_filename,
                gcs_path = gcs_path,
                content_type = file.content_type or 'application/octet-stream',
                project_id = project.id
            )

            # Save image metadata to SQL database
            try:
                db.session.add(image_metadata)
                db.session.commit()
            except SQLAlchemyError as e:
                db.session.rollback()
                print(f"Database error while uploading image metadata for file {gcs_path}: {str(e.orig)}")
                _delete_file_from_gcs(gcs_path)
                abort(500, message = "Database error occurred while saving image metadata. Rolled back successfully")
            
            return image_metadata
    

# Get all images that belong to the user
    @jwt_required()
    @blp.response(200, PlainImageSchema(many = True))
    def get(self, project_id):
        current_user_id = get_jwt_identity()
        project = ProjectModel.query.filter_by(id = project_id, user_id = current_user_id).first_or_404(
            description = "Project not found or access denied"
        )

        return project.images.all()
    

# Manage individual images, like metadata and deletion
@blp.route("/images/<int:image_id>")
class ImageResource(MethodView):
    @jwt_required()
    @blp.response(200, PlainImageSchema)
    def get(self, image_id):
        # Retrieve user credentials
        current_user_id = get_jwt_identity()
        # Search for their project by user -> project, and image id
        image = db.session.query(ImageModel).join(ProjectModel).filter(
            ImageModel.id == image_id,
            ProjectModel.user_id == current_user_id
        ).first_or_404(description="Image not found or access denied")
        return image

    @jwt_required()
    @blp.response(200, {"message": "Image deleted successfully."}) 
    def delete(self, image_id):
        # Delete a specific image (metadata from DB and file from GCS)
        current_user_id = get_jwt_identity()
        image = db.session.query(ImageModel).join(ProjectModel).filter(
            ImageModel.id == image_id,
            ProjectModel.user_id == current_user_id
        ).first_or_404(description="Image not found or access denied.")

        gcs_path_to_delete = image.gcs_path

        try:
            db.session.delete(image)
            # Attempt GCS delete. If it fails, the DB record is already marked for deletion
            if not _delete_file_from_gcs(gcs_path_to_delete):
                print(f"Warning: Image metadata for {gcs_path_to_delete} deleted from DB, but GCS file deletion may have failed or was skipped")
            
            db.session.commit() 
            
        except SQLAlchemyError as e:
            db.session.rollback()
            abort(500, message=f"Database error deleting image: {str(e)}")

        return {"message": "Image deleted successfully"}
