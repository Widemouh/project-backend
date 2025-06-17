'''
----------------------------
Gemini API (to provide label context)
NOT BY USER INTERACTION
----------------------------
'''

import os
from flask_smorest import Blueprint

from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel


# Gemini API blueprint
blp = Blueprint("Gemini", __name__, description = "Gemini AI for content generation through labels")

# Gemini API setup
# IMPORTANT: These should ideally be loaded from environment variables
# especially for production. For dev, hardcoding is okay for now.
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT_ID", "second-metrics-461420-e7")
REGION = os.getenv("GOOGLE_CLOUD_REGION", "us-central1")
MODEL_ID = os.getenv("GOOGLE_CLOUD_GEMINI_MODEL_ID") 

# Ensures model is initialized once
class GeminiService:
    _model = None

    def __init__(self, project_id: str, region: str, model_id: str):
        if not GeminiService._model:
            try:
                aiplatform.init(project=project_id, location=region)
                GeminiService._model = GenerativeModel(model_id)
                print(f"Vertex AI SDK initialized for project {project_id} in {region}")
            except Exception as e:
                print(f"Error initializing Vertex AI SDK: {e}. Check your project ID, region, API enablement, and 'gcloud auth application-default login'.")
                # Model state is None if initialization fails
                GeminiService._model = None

    def refine_label_text(self, label_text: str, difficulty: str, project_name: str, project_description: str) -> str:
        # Generates refined text for a given label based on the specified difficulty        
        if not GeminiService._model:
            print("GeminiService: _model not initialized. Cannot refine text.")
            raise ConnectionError("Gemini service model not available or not initialized.")

        if difficulty == "simple":
            prompt = f"Do not provide any follow up questions, you are creating content single-use for a client. Provide a brief overview, along with a checklist and strong guidance steps for a beginner to complete the '{label_text}' part of a '{project_name}' project. You are given the following overview for this project: '{project_description}'"
        elif difficulty == "intermediate":
            prompt = f"Do not provide any follow up questions, you are creating content single-use for a client. Provide a brief overview, along with a well-described checklist and well-explained guidance steps for an intermediate to complete the '{label_text}' part of a '{project_name}' project. You are given the following overview for this project: '{project_description}'"
        elif difficulty == "in_depth":
            prompt = f"Do not provide any follow up questions, you are creating content single-use for a client. Provide a brief overview, along with a checklist and guidance steps to complete the '{label_text}' part of a '{project_name}' project at a challenging level, assuming the user is very skilled. You are given the following overview for this project: '{project_description}'"

        try:
            print(f"GeminiService: Sending prompt for label '{label_text}', difficulty '{difficulty}'")
            response = GeminiService._model.generate_content(prompt)
            # Check for empty response from Gemini
            if not response.text: 
                print(f"GeminiService: Received empty response for label '{label_text}', difficulty '{difficulty}'")
                # Raise an error to indicate an issue
                raise ConnectionError(f"Gemini returned an empty response for label '{label_text}' with difficulty '{difficulty}'.")
            return response.text
        except Exception as e:
            print(f"GeminiService: Error generating content for label '{label_text}', difficulty '{difficulty}': {e}")
            raise ConnectionError(f"Failed to get refinement from Gemini for label '{label_text}': {e}")


# Initialize the GeminiService
# This is an instance of the large GeminiService class
# This gives us access to refine_label_text service wherever we need
gemini_service_instance = GeminiService(PROJECT_ID, REGION, MODEL_ID)
