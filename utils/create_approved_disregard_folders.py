import requests
import json
import time

ZOHO_CLIENT_ID     = "1000.1553ED62RZUMKKXBU11108F3R60XRM"
ZOHO_CLIENT_SECRET = "765799a817efa11d1acfb8a199df0df7361a4d6e9b"
ZOHO_REFRESH_TOKEN = "1000.0e95c5e72c1fbc08725da468c1777e47.4d30b8d31725a330c2e2bbb252436023"
PARENT_FOLDER_ID   = "1jvesd739f3203a31410096fd941bc9a1d52f"

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

def main():
    print("[ZOHO START] Fetching access token...")
    access_token = get_access_token()
    print("[ZOHO START] Access token retrieved successfully.")
    
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Accept":        "application/vnd.api+json",
    }
    
    # 1. List all category folders under parent 'Lighting Fixtures'
    print(f"\n[1] Listing all folders under parent folder: '{PARENT_FOLDER_ID}'...")
    list_url = f"https://workdrive.zoho.com/api/v1/files/{PARENT_FOLDER_ID}/files"
    res = requests.get(list_url, headers=headers)
    if res.status_code != 200:
        print(f"Error listing parent folders: {res.text}")
        return
        
    category_folders = []
    for item in res.json().get("data", []):
        attrs = item.get("attributes", {})
        if attrs.get("type") == "folder":
            category_folders.append({
                "name": attrs.get("name"),
                "id": item.get("id")
            })
            
    print(f"Found {len(category_folders)} category folders in Zoho:")
    for f in category_folders:
        print(f"  - {f['name']} (ID: {f['id']})")
        
    # 2. For each category folder, check and create Approved & Disregard subfolders
    create_url = "https://workdrive.zoho.com/api/v1/files"
    
    print("\n[2] Scanning subfolders inside each category...")
    for cat in category_folders:
        cat_name = cat["name"]
        cat_id = cat["id"]
        
        print(f"\n" + "-" * 50)
        print(f"Scanning category: '{cat_name}' (ID: {cat_id})")
        
        # List items inside this category folder
        sub_list_url = f"https://workdrive.zoho.com/api/v1/files/{cat_id}/files"
        sub_res = requests.get(sub_list_url, headers=headers)
        
        approved_found = False
        disregard_found = False
        
        if sub_res.status_code == 200:
            for item in sub_res.json().get("data", []):
                attrs = item.get("attributes", {})
                name_lower = attrs.get("name", "").strip().lower()
                if attrs.get("type") == "folder":
                    if name_lower == "approved":
                        approved_found = True
                        print(f"  [OK] Found existing 'Approved' subfolder.")
                    elif name_lower in ("disregard", "disregarded", "rejected"):
                        disregard_found = True
                        print(f"  [OK] Found existing 'Disregard' subfolder.")
        else:
            print(f"  [ERROR] Could not list subfolders: {sub_res.text}")
            
        # Create 'Approved' folder if missing
        if not approved_found:
            print(f"  [MISSING] 'Approved' subfolder is missing. Creating it...")
            payload = {
                "data": {
                    "attributes": {"name": "Approved", "parent_id": cat_id},
                    "type":       "files",
                }
            }
            try:
                c_res = requests.post(create_url, headers={**headers, "Content-Type": "application/json"}, json=payload)
                if c_res.status_code in (200, 201):
                    new_id = c_res.json().get("data", {}).get("id")
                    print(f"  -> [CREATED] 'Approved' folder successfully! (ID: {new_id})")
                else:
                    print(f"  -> [FAILED] Could not create 'Approved' folder: {c_res.text}")
            except Exception as e:
                print(f"  -> [ERROR] Exception creating 'Approved': {e}")
            time.sleep(0.3)
            
        # Create 'Disregard' folder if missing
        if not disregard_found:
            print(f"  [MISSING] 'Disregard' subfolder is missing. Creating it...")
            payload = {
                "data": {
                    "attributes": {"name": "Disregard", "parent_id": cat_id},
                    "type":       "files",
                }
            }
            try:
                c_res = requests.post(create_url, headers={**headers, "Content-Type": "application/json"}, json=payload)
                if c_res.status_code in (200, 201):
                    new_id = c_res.json().get("data", {}).get("id")
                    print(f"  -> [CREATED] 'Disregard' folder successfully! (ID: {new_id})")
                else:
                    print(f"  -> [FAILED] Could not create 'Disregard' folder: {c_res.text}")
            except Exception as e:
                print(f"  -> [ERROR] Exception creating 'Disregard': {e}")
            time.sleep(0.3)
            
    print("\n" + "-" * 50)
    print("[ZOHO DONE] Completed scanning and folder creation for all categories!")

if __name__ == "__main__":
    main()
