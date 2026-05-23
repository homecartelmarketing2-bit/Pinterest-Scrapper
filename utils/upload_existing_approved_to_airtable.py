import requests
import json
import time
import os
import sys

# Ensure parent directory is in the path for proper imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scrape_and_upload import (
    get_access_token,
    create_zoho_share_link,
    AIRTABLE_TOKEN,
    AIRTABLE_BASE_ID,
    AIRTABLE_TABLE,
    AIRTABLE_VIEW,
    push_photo_and_prompts
)

CHANDELIER_APPROVED_FOLDER = "ambg55491197ac32c45c3b0d4e5bb7f07d834"

def get_zoho_approved_files(access_token):
    """List all files in the Chandelier Approved folder in Zoho WorkDrive, sorted newest to oldest."""
    url = f"https://workdrive.zoho.com/api/v1/files/{CHANDELIER_APPROVED_FOLDER}/files"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Accept":        "application/vnd.api+json",
    }
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            files = []
            for item in res.json().get("data", []):
                attrs = item.get("attributes", {})
                if attrs.get("type") != "folder":
                    files.append({
                        "id": item.get("id"),
                        "name": attrs.get("name"),
                        "created_time_ms": attrs.get("created_time_in_millisecond", 0)
                    })
            # Sort files newest to oldest (largest created_time_ms first)
            files.sort(key=lambda x: x.get("created_time_ms", 0), reverse=True)
            return files
        else:
            print(f"[ZOHO] Error listing files in Approved folder: {res.text}")
    except Exception as e:
        print(f"[ZOHO] Exception listing files: {e}")
    return []

def clear_all_standby_records():
    """Clear Reference Photo, Styled Photo, and Styled Photo Prompt fields for all Standby records to start fresh."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type":  "application/json",
    }
    # Find all Standby records
    params = {
        "view":            AIRTABLE_VIEW,
        "filterByFormula": "{Status} = 'Standby'",
        "maxRecords":      150
    }
    try:
        print("[CLEAR] Listing Standby records in Airtable to clear...")
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code == 200:
            records = resp.json().get("records", [])
            print(f"[CLEAR] Found {len(records)} Standby records in Airtable to clean up...")
            cleaned = 0
            for record in records:
                fields = record.get("fields", {})
                record_id = record.get("id")
                sku = fields.get("SKU Code", "N/A")
                
                # Check if fields are populated
                if fields.get("Reference Photo") or fields.get("Styled Photo") or fields.get("Styled Photo Prompt"):
                    payload = {
                        "fields": {
                            "Reference Photo": None,
                            "Styled Photo": None,
                            "Styled Photo Prompt": None
                        }
                    }
                    p_resp = requests.patch(f"{url}/{record_id}", headers=headers, json=payload, timeout=15)
                    if p_resp.status_code == 200:
                        cleaned += 1
            print(f"[CLEAR] Successfully cleared {cleaned} populated Standby records!")
        else:
            print(f"[CLEAR] Error listing records: {resp.text}")
    except Exception as e:
        print(f"[CLEAR] Exception clearing records: {e}")

def download_zoho_file(access_token, file_id, filename):
    """Download file bytes directly using a temporary public share link from Zoho."""
    share_url = create_zoho_share_link(access_token, file_id, filename)
    if not share_url:
        print(f"  [DOWNLOAD] Failed to create Zoho share link for download.")
        return None
    try:
        resp = requests.get(share_url, timeout=30)
        if resp.status_code == 200:
            return resp.content
        print(f"  [DOWNLOAD] Failed to download from share link: status {resp.status_code}")
    except Exception as e:
        print(f"  [DOWNLOAD] Exception downloading from share link: {e}")
    return None

def main():
    print("[BATCH START] Fetching Zoho access token...")
    access_token = get_access_token()
    print("[ZOHO] Access token retrieved successfully.")
    
    # Clean up Standby Airtable fields to ensure a fresh, perfectly aligned gap layout
    clear_all_standby_records()
    
    print(f"\n[1] Listing approved files inside Zoho Chandelier Approved folder ('{CHANDELIER_APPROVED_FOLDER}')...")
    approved_files = get_zoho_approved_files(access_token)
    print(f"Found {len(approved_files)} approved files in Zoho (sorted newest to oldest).")
    
    if not approved_files:
        print("[BATCH DONE] No approved files found in Zoho Chandelier Approved folder. Exiting.")
        return
        
    print(f"\n[2] Starting batch prompt and attachment pipeline (Max {len(approved_files)} operations)...")
    
    success_count = 0
    for idx, zoho_file in enumerate(approved_files):
        print(f"\n" + "="*60)
        print(f"Processing Chandelier {idx+1}/{len(approved_files)}:")
        print(f"  Zoho File: {zoho_file['name']} (ID: {zoho_file['id']})")
        
        # 1. Download image bytes from Zoho
        print("  Downloading file from Zoho...")
        image_bytes = download_zoho_file(access_token, zoho_file["id"], zoho_file["name"])
        if not image_bytes:
            print("  [X] Failed to download file from Zoho. Skipping.")
            continue
            
        # 2. Determine MIME type
        lower_name = zoho_file["name"].lower()
        if ".png" in lower_name:
            mime = "image/png"
        elif ".webp" in lower_name:
            mime = "image/webp"
        else:
            mime = "image/jpeg"
            
        # 3. Trigger premium room interior designer push pipeline
        print("  Launching premium push pipeline (1 photo attached to 'Reference Photo', 5 prompts generated)...")
        try:
            push_photo_and_prompts(
                access_token=access_token,
                file_id=zoho_file["id"],
                filename=zoho_file["name"],
                image_bytes=image_bytes,
                mime=mime,
                category="Architectural Digest sculptural Chandeliers"
            )
            success_count += 1
        except Exception as e:
            print(f"  [X] Error during push pipeline: {e}")
            
        time.sleep(1.0)  # Safe breathing room between LLM requests and Airtable uploads
        
    print(f"\n[BATCH DONE] Successfully processed {success_count}/{len(approved_files)} approved chandeliers into Airtable!")

if __name__ == "__main__":
    main()
