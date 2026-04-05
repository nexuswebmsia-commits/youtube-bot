import os
import base64
import pickle
import tempfile

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

CLIENT_SECRETS_FILE = os.environ.get("CLIENT_SECRETS_FILE", "client_secret.json")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"

def _load_credentials_from_env():
    token_b64 = os.environ.get("YOUTUBE_TOKEN_B64")
    if not token_b64:
        return None
    try:
        return pickle.loads(base64.b64decode(token_b64))
    except Exception as e:
        print(f"Warning: could not decode YOUTUBE_TOKEN_B64: {e}")
        return None

def _get_client_secrets_path():
    secret_b64 = os.environ.get("YOUTUBE_CLIENT_SECRET_B64")
    if secret_b64:
        try:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
            tmp.write(base64.b64decode(secret_b64))
            tmp.close()
            return tmp.name
        except Exception as e:
            print(f"Warning: could not decode YOUTUBE_CLIENT_SECRET_B64: {e}")
    return CLIENT_SECRETS_FILE

def get_authenticated_service():
    credentials = _load_credentials_from_env()
    if credentials is None and os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            credentials = pickle.load(token)
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    if not credentials or not credentials.valid:
        secrets_path = _get_client_secrets_path()
        flow = InstalledAppFlow.from_client_secrets_file(secrets_path, SCOPES)
        credentials = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as token:
            pickle.dump(credentials, token)
    return credentials
