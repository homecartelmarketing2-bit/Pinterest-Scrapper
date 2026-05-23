import requests
import json

ZOHO_CLIENT_ID = "1000.1553ED62RZUMKKXBU11108F3R60XRM"
ZOHO_CLIENT_SECRET = "765799a817efa11d1acfb8a199df0df7361a4d6e9b"
ZOHO_REFRESH_TOKEN = "1000.0e95c5e72c1fbc08725da468c1777e47.4d30b8d31725a330c2e2bbb252436023"
PARENT_FOLDER_ID = "1jvesd739f3203a31410096fd941bc9a1d52f"

# 1. Get Access Token
token_url = "https://accounts.zoho.com/oauth/v2/token"
data = {
    "refresh_token": ZOHO_REFRESH_TOKEN,
    "client_id": ZOHO_CLIENT_ID,
    "client_secret": ZOHO_CLIENT_SECRET,
    "grant_type": "refresh_token"
}

response = requests.post(token_url, data=data)
if response.status_code != 200:
    print(f"Error getting token: {response.text}")
    exit(1)

access_token = response.json().get("access_token")
print("Access token retrieved successfully.")

# 2. Create Folders
folders = [
    "Ceiling Lights",
    "Semi Flush Mounted Lights",
    "Chandeliers",
    "Cluster Chandeliers",
    "Pendant Lights",
    "Floor Lamps",
    "Table Lamps",
    "Rechargeable Table Lamps",
    "Wall Lights",
    "Painting & Bathroom Lights"
]

create_url = "https://workdrive.zoho.com/api/v1/files"
headers = {
    "Authorization": f"Zoho-oauthtoken {access_token}",
    "Accept": "application/vnd.api+json",
    "Content-Type": "application/json"
}

for folder_name in folders:
    payload = {
        "data": {
            "attributes": {
                "name": folder_name,
                "parent_id": PARENT_FOLDER_ID
            },
            "type": "files"
        }
    }
    
    res = requests.post(create_url, headers=headers, json=payload)
    if res.status_code == 201 or res.status_code == 200:
        print(f"Successfully created folder: {folder_name}")
    else:
        print(f"Failed to create folder: {folder_name} - Status: {res.status_code} - {res.text}")
