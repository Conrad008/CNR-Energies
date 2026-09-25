import base64
import requests
from datetime import datetime
from django.conf import settings

class MpesaError(Exception):
    pass

def get_access_token():
    resp = requests.get(
        f"{settings.MPESA_BASE_URL}/oauth/v1/generate?grant_type=client_credentials",
        auth=(settings.MPESA_CONSUMER_KEY, settings.MPESA_CONSUMER_SECRET),
        timeout=10,
    )
    if resp.status_code != 200:
        raise MpesaError(f"Could not authenticate with M-Pesa: {resp.text}")
    return resp.json()['access_token']