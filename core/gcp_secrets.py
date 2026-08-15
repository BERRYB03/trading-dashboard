import os
try:
    from google.cloud import secretmanager
except ImportError:
    secretmanager = None

# For local testing, we fallback to env vars if running locally without GCP ADC.
# In production on GCE, Application Default Credentials will automatically handle auth.
# Ensure the Compute Engine service account has the 'Secret Manager Secret Accessor' role.

def get_secret(secret_id, version_id="latest"):
    """
    Dynamically fetches a secret from Google Cloud Secret Manager.
    Assumes the GCP Project ID is available in the environment or ADC.
    """
    project_id = os.getenv("GCP_PROJECT_ID")
    
    # Fallback to local environment if GCP Project ID is missing or secretmanager isn't installed
    if not project_id or secretmanager is None:
        print(f"[WARNING] GCP_PROJECT_ID missing. Falling back to local env for {secret_id}")
        return os.getenv(secret_id, "")
        
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        print(f"[CRITICAL ERROR] Failed to fetch {secret_id} from GCP Secret Manager: {e}")
        # Final fallback to local .env if Secret Manager fails during migration
        return os.getenv(secret_id, "")

if __name__ == "__main__":
    # Test execution
    print("Testing GCP Secret Manager Interface...")
    mock_key = get_secret("TEST_SECRET")
    print(f"Result: {mock_key if mock_key else 'None/Empty'}")
