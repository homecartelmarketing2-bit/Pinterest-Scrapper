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

# List files
url = f"https://workdrive.zoho.com/api/v1/files/{PARENT_FOLDER_ID}/files"
headers = {
    "Authorization": f"Zoho-oauthtoken {access_token}",
    "Accept": "application/vnd.api+json"
}

res = requests.get(url, headers=headers)
print("Status:", res.status_code)
payload = res.json()
data = payload.get("data", [])
for item in data:
    attrs = item.get("attributes", {})
    print(f"Name: {attrs.get('name')}, ID: {item.get('id')}, Type: {attrs.get('type')}")
