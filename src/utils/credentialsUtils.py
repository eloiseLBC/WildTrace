import os
import sys
import json
from google.oauth2 import service_account
from google.auth.transport.requests import Request
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


def generate_credentials_google_drive():
    """
    Génère les credentials pour Google Drive.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    service_account_file = os.path.join(base_dir, '../../my_secrets/service-account.json')
    scopes = ['https://www.googleapis.com/auth/drive']  # Accès complet

    credentials = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=scopes)

    # Si le token n’existe pas ou est expiré, on le rafraîchit
    if not credentials.valid or credentials.expired:
        credentials.refresh(Request())

    token_data = {
        "access_token": credentials.token,
        "expires_at": credentials.expiry.isoformat() if credentials.expiry else None
    }
    # Sauvegarde dans un .json
    with open(os.path.join(base_dir, '../../my_secrets/drive_token.json'), 'w') as f:
        json.dump(token_data, f, indent=4)