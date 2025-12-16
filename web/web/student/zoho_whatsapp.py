import requests
from dotenv import load_dotenv
from pathlib import Path
import os
load_dotenv(Path(__file__).resolve().parents[2] / '.env')


CHATRACE_API_KEY = os.getenv("NEW_CHATRACE_TOKEN")  
CHATRACE_BASE_URL = os.getenv("NEW_CHATRACE_API")
url = f"{CHATRACE_BASE_URL}/users"

def whatsapp_add(self,phone,name,email,batchno,username,password):
    payload = {
        "phone": phone,
        "first_name": name,
        "actions": [
            {"action": "add_tag", "tag_name": "SP_Onboard"},
            {"action": "set_field_value", "field_name": "email", "value": email},
            {"action": "set_field_value", "field_name": "SP_BatchID", "value": batchno},
            {"action": "set_field_value", "field_name": "SP_Username", "value": username},
            {"action": "set_field_value", "field_name": "SP_Password", "value": password}
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-ACCESS-TOKEN": CHATRACE_API_KEY
    }

    response = requests.post(url, json=payload, headers=headers)
    try:
        response.raise_for_status()
        print("Request successful:", response.json())
    except requests.exceptions.HTTPError as err:
        print(f"Request failed ({response.status_code}): {err}")
    return response.json()