from google.cloud import storage
from google.cloud import aiplatform
from vertexai.preview.generative_models import GenerativeModel, Part
import json
import os
from datetime import datetime
from google.oauth2 import service_account
import google.auth
from google.auth.exceptions import DefaultCredentialsError

class GCPIntegrations:
    def __init__(self, project_id, location="us-central1", credentials_path=None):
        self.project_id = project_id
        self.location = location
        self.credentials = None
        self.initialize_credentials(credentials_path)
        
    def initialize_credentials(self, credentials_path=None):
        """Initialize GCP credentials with explicit error handling"""
        try:
            # First try explicit credentials if path is provided
            print("In initialization of gcp")
            if credentials_path and os.path.exists(credentials_path):
                self.credentials = service_account.Credentials.from_service_account_file(
                    credentials_path,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                print("Using provided service account credentials")
            else:
                print("In initialization of gcp else")
                # Try environment variable
                env_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
                if env_creds and os.path.exists(env_creds):
                    self.credentials = service_account.Credentials.from_service_account_file(
                        env_creds,
                        scopes=['https://www.googleapis.com/auth/cloud-platform']
                    )
                    print("Using credentials from GOOGLE_APPLICATION_CREDENTIALS")
                else:
                    # Try default credentials
                    self.credentials, project = google.auth.default()
                    print("Using default credentials")
            
            # Initialize clients with credentials
            self.storage_client = storage.Client(
                project=self.project_id,
                credentials=self.credentials
            )
            
            # Initialize Vertex AI
            aiplatform.init(
                project=self.project_id,
                location=self.location,
                credentials=self.credentials
            )
            
        except DefaultCredentialsError as e:
            error_msg = (
                "GCP credentials not found. Please ensure either:\n"
                "1. GOOGLE_APPLICATION_CREDENTIALS environment variable is set\n"
                "2. Service account key file is provided\n"
                "3. Default application credentials are available"
            )
            print(error_msg)
            raise Exception(error_msg) from e
        except Exception as e:
            error_msg = f"Failed to initialize GCP credentials: {str(e)}"
            print(error_msg)
            raise Exception(error_msg) from e
            
    def verify_bucket_access(self, bucket_name):
        """Verify access to the specified bucket"""
        try:
            bucket = self.storage_client.bucket(bucket_name)
            # Try to access bucket metadata to verify permissions
            bucket.reload()
            return True
        except Exception as e:
            error_msg = (
                f"Failed to access bucket {bucket_name}. "
                f"Please verify bucket exists and service account has proper permissions.\n"
                f"Error: {str(e)}"
            )
            print(error_msg)
            return False
            
    def upload_to_gcs(self, file_path, bucket_name):
        """Upload file to Google Cloud Storage with improved error handling"""
        try:
            # Verify file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
                
            # Verify bucket access
            if not self.verify_bucket_access(bucket_name):
                raise Exception(f"Cannot access bucket: {bucket_name}")
                
            bucket = self.storage_client.bucket(bucket_name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            blob_name = f"recordings/{timestamp}_{os.path.basename(file_path)}"
            blob = bucket.blob(blob_name)
            
            # Upload with explicit content type
            content_type = 'video/mp4' if file_path.endswith('.mp4') else 'application/octet-stream'
            blob.upload_from_filename(
                file_path,
                content_type=content_type,
                timeout=300  # 5 minute timeout for large files
            )
            
            # Make the file publicly accessible
            blob.make_public()
            
            return {
                'public_url': blob.public_url,
                'gcs_uri': f"gs://{bucket_name}/{blob_name}"
            }
        except Exception as e:
            error_msg = f"Error uploading to GCS: {str(e)}"
            print(error_msg)
            raise Exception(error_msg) from e
            
    def process_recording(self, video_path, interaction_path, bucket_name):
        """Process recording with improved error handling"""
        try:
            # First verify credentials are valid
            if not self.credentials:
                raise Exception("GCP credentials not initialized")
                
            # Upload video
            print(f"Uploading video: {video_path}")
            upload_result = self.upload_to_gcs(video_path, bucket_name)
            if not upload_result:
                raise Exception("Failed to upload video to GCS")
                
            # Load interaction data
            print("Loading interaction data")
            with open(interaction_path, 'r') as f:
                interaction_data = json.load(f)
                
            # Analyze with Gemini
            print("Analyzing with Gemini")
            workflow_data = self.analyze_video_with_gemini(
                upload_result['public_url'],
                interaction_data
            )
            
            if not workflow_data:
                raise Exception("Failed to analyze video with Gemini")
                
            return workflow_data
            
        except Exception as e:
            error_msg = f"Error in process_recording: {str(e)}"
            print(error_msg)
            raise Exception(error_msg) from e
            
    def analyze_video_with_gemini(self, video_url, interaction_data):
        """Analyze video using Gemini Pro Vision model with improved error handling"""
        try:
            # Initialize Gemini Pro Vision model
            model = GenerativeModel("gemini-pro")
            
            # Craft the prompt
            prompt = f"""Analyze this screen recording video and interaction data to create a structured workflow JSON.
            The video shows a user interacting with an application interface.
            
            Focus on:
            1. The overall system goal
            2. Main activities performed
            3. Detailed steps within each activity
            4. UI interactions (clicks, typing, navigation)
            5. Screen elements and their states
            
            Video URL: {video_url}
            
            User Interaction Data:
            {json.dumps(interaction_data, indent=2)}
            
            Generate a JSON response with this structure:
            {{
                "system_goal": "Brief description of what the user is trying to accomplish",
                "activities_for_goal": ["list of activity numbers"],
                "activities": [
                    {{
                        "activity_name": "Name of the activity",
                        "activity_no": "Sequential number",
                        "activity_steps": [
                            {{
                                "activity_step_no": "Step number within activity",
                                "activity_step_rationale": "Why this step is needed",
                                "activity_step_type": "Type of interaction (Click, Type, etc)",
                                "activity_step_control": "UI element interacted with",
                                "activity_step_desc": "What the user did",
                                "activity_screen_desc": "What was visible on screen"
                            }}
                        ]
                    }}
                ]
            }}"""
            
            # Call Gemini model with error handling
            try:
                response = model.generate_content(
                    [prompt],
                    generation_config={
                        "temperature": 0.2,
                        "top_p": 0.8,
                        "top_k": 40
                    }
                )
                
                # Parse and validate the response
                try:
                    workflow_json = json.loads(response.text)
                    return workflow_json
                except json.JSONDecodeError as e:
                    print(f"Error: Invalid JSON in model response: {e}")
                    print("Raw response:", response.text)
                    return None
                    
            except Exception as e:
                print(f"Error calling Gemini model: {e}")
                return None
                
        except Exception as e:
            error_msg = f"Error analyzing video with Gemini: {str(e)}"
            print(error_msg)
            raise Exception(error_msg) from e