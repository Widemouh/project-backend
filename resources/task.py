'''
----------------------------
Cleanup revoked user tokens
NOT BY USER INTERACTION
----------------------------
'''
import os
from flask.views import MethodView
from flask_smorest import Blueprint
from flask import request, abort

# Imports for OIDC token verification
from google.oauth2 import id_token
from google.auth.transport import requests

from clean_up import cleanup_revoked_tokens


blp = Blueprint("tasks", __name__, description = "Endpoints for scheduled tasks")

cloud_run_url = os.getenv("CLOUD_RUN_SERVICE_URL")

@blp.route("/tasks/cleanup-revoked-tokens")
class CleanupTask(MethodView):
    def post(self):
        # Security check for Cloud Run
        try:
            # Get the OIDC token from the Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                print("Missing or invalid Authorization header")
                abort(401)

            token = auth_header.split(" ")[1]

            # Verify the token
            id_token.verify_oauth2_token(token, requests.Request(), audience = cloud_run_url)
            
        except Exception as e:
            # This will catch any error in token verification
            print(f"Token verification failed: {e}")
            abort(401)

        # Proceed with cleanup once verified
        print("Starting cleanup job")
        cleanup_revoked_tokens()
        return {"message": "Cleanup of revoked tokens completed"}, 200
