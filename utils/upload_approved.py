import os
import requests
import json

ZOHO_CLIENT_ID     = "1000.1553ED62RZUMKKXBU11108F3R60XRM"
ZOHO_CLIENT_SECRET = "765799a817efa11d1acfb8a199df0df7361a4d6e9b"
ZOHO_REFRESH_TOKEN = "1000.0e95c5e72c1fbc08725da468c1777e47.4d30b8d31725a330c2e2bbb252436023"
PARENT_FOLDER_ID   = "1jvesd739f3203a31410096fd941bc9a1d52f"

APPROVED_FILES = [
    "scraped_0.jpg",
    "scraped_2.jpg",
    "scraped_4.jpg",
    "scraped_5.jpg"
]
CATEGORY = "Chandeliers"

def get_access_token():
    token_url = "https://accounts.zoho.com/oauth/v2/token"
    data = {
        "refresh_token": ZOHO_REFRESH_TOKEN,
        "client_id":     ZOHO_CLIENT_ID,
        "client_secret": ZOHO_CLIENT_SECRET,
        "grant_type":    "refresh_token",
    }
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    return response.json().get("access_token")

def get_folder_id(access_token, name):
    url = f"https://workdrive.zoho.com/api/v1/files/{PARENT_FOLDER_ID}/files"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Accept":        "application/vnd.api+json",
    }
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    for item in res.json().get("data", []):
        if item["attributes"]["name"] == name:
            return item["id"]
    return None

def main():
    token = get_access_token()
    folder_id = get_folder_id(token, CATEGORY)
    if not folder_id:
        print(f"Error: Folder '{CATEGORY}' not found.")
        return

    for filename in APPROVED_FILES:
        filepath = os.path.join("scraped_raw", filename)
        if not os.path.exists(filepath):
            print(f"Skipping {filename}, not found.")
            continue
        
        print(f"Uploading {filename}...")
        with open(filepath, "rb") as f:
            upload_resp = requests.post(
                "https://workdrive.zoho.com/api/v1/upload",
                headers={"Authorization": f"Zoho-oauthtoken {token}"},
                files={"content": (f"{CATEGORY}_{filename}", f)},
                data={"parent_id": folder_id, "override-name-exist": "true"},
            )
        if upload_resp.status_code in (200, 201):
            print(f"  Successfully uploaded {filename}")
        else:
            print(f"  Failed: {upload_resp.text}")

if __name__ == "__main__":
    main()
