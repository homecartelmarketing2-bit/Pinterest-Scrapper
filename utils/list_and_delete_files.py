import requests

ZOHO_CLIENT_ID = "1000.1553ED62RZUMKKXBU11108F3R60XRM"
ZOHO_CLIENT_SECRET = "765799a817efa11d1acfb8a199df0df7361a4d6e9b"
ZOHO_REFRESH_TOKEN = "1000.0e95c5e72c1fbc08725da468c1777e47.4d30b8d31725a330c2e2bbb252436023"
PARENT_FOLDER_ID = "1jvesd739f3203a31410096fd941bc9a1d52f"

# Get Access Token
token_url = "https://accounts.zoho.com/oauth/v2/token"
data = {
    "refresh_token": ZOHO_REFRESH_TOKEN,
    "client_id": ZOHO_CLIENT_ID,
    "client_secret": ZOHO_CLIENT_SECRET,
    "grant_type": "refresh_token"
}

response = requests.post(token_url, data=data)
access_token = response.json().get("access_token")

# List folders first
url = f"https://workdrive.zoho.com/api/v1/files/{PARENT_FOLDER_ID}/files"
headers = {
    "Authorization": f"Zoho-oauthtoken {access_token}",
    "Accept": "application/vnd.api+json"
}

res = requests.get(url, headers=headers)
payload = res.json()
folders = payload.get("data", [])

found_file = None
for folder in folders:
    folder_id = folder.get("id")
    folder_name = folder.get("attributes", {}).get("name")
    
    # List files in this folder
    f_url = f"https://workdrive.zoho.com/api/v1/files/{folder_id}/files"
    f_res = requests.get(f_url, headers=headers)
    f_payload = f_res.json()
    files = f_payload.get("data", [])
    if files:
        found_file = files[0]
        print(f"Found a file inside folder '{folder_name}': {found_file.get('attributes', {}).get('name')} ({found_file.get('id')})")
        break

if not found_file:
    print("No files found inside folders to test deletion on.")
    exit(0)

file_id = found_file.get("id")

# Try DELETE on the file
print(f"Testing DELETE on file {file_id}...")
del_res = requests.delete(f"https://workdrive.zoho.com/api/v1/files/{file_id}", headers=headers)
print("DELETE Status code:", del_res.status_code)
print("DELETE Response:", del_res.text[:300])

# Try PATCH with status = trash on the file
print(f"Testing PATCH with status='trash' on file {file_id}...")
patch_headers = {
    "Authorization": f"Zoho-oauthtoken {access_token}",
    "Content-Type": "application/json",
    "Accept": "application/vnd.api+json"
}
patch_payload = {
    "data": {
        "type": "files",
        "attributes": {
            "status": "trash"
        }
    }
}
patch_res = requests.patch(f"https://workdrive.zoho.com/api/v1/files/{file_id}", headers=patch_headers, json=patch_payload)
print("PATCH Status code:", patch_res.status_code)
print("PATCH Response:", patch_res.text[:300])
