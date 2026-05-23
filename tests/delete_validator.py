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

# List files to find one to delete
url = f"https://workdrive.zoho.com/api/v1/files/{PARENT_FOLDER_ID}/files"
headers = {
    "Authorization": f"Zoho-oauthtoken {access_token}",
    "Accept": "application/vnd.api+json"
}

res = requests.get(url, headers=headers)
payload = res.json()
data_list = payload.get("data", [])

if not data_list:
    print("No folders found to delete.")
    exit(0)

# Try deleting the first folder using PATCH status = trashed
target_folder = data_list[0]
target_id = target_folder.get("id")
target_name = target_folder.get("attributes", {}).get("name")

print(f"Attempting to PATCH folder: {target_name} ({target_id})")

patch_url = f"https://workdrive.zoho.com/api/v1/files/{target_id}"
patch_headers = {
    "Authorization": f"Zoho-oauthtoken {access_token}",
    "Content-Type": "application/json",
    "Accept": "application/vnd.api+json"
}

payloads = [
    {"status": 1},
    {"status": "trash"},
    {"data": {"type": "files", "attributes": {"status": 1}}},
    {"data": {"type": "files", "attributes": {"status": "trash"}}}
]

for i, p in enumerate(payloads, 1):
    patch_res = requests.patch(patch_url, headers=patch_headers, json=p)
    print(f"Test {i} (payload {p}) - Status: {patch_res.status_code}")
    print("Response text:", patch_res.text[:300])
