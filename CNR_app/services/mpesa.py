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

def stk_push(phone_number, amount, account_reference, description):
    token = get_access_token()
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    password = base64.b64encode(
        f"{settings.MPESA_SHORTCODE}{settings.MPESA_PASSKEY}{timestamp}".encode()
    ).decode()

    payload = {
        "BusinessShortCode": settings.MPESA_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone_number,
        "PartyB": settings.MPESA_SHORTCODE,
        "PhoneNumber": phone_number,
        "CallBackURL": settings.MPESA_CALLBACK_URL,
        "AccountReference": account_reference[:12],
        "TransactionDesc": description[:13],
    }

    resp = requests.post(
        f"{settings.MPESA_BASE_URL}/mpesa/stkpush/v1/processrequest",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    data = resp.json()
    if resp.status_code != 200 or data.get('ResponseCode') != '0':
        raise MpesaError(data.get('errorMessage') or data.get('ResponseDescription') or 'STK push failed')
    return data