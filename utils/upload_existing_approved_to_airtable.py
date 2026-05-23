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
    AIRTABLE_VIEW
)

CHANDELIER_APPROVED_FOLDER = "ambg55491197ac32c45c3b0d4e5bb7f07d834"

def get_zoho_approved_files(access_token):
    """List all files in the Chandelier Approved folder in Zoho WorkDrive."""
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
                        "name": attrs.get("name")
                    })
            return files
        else:
            print(f"[ZOHO] Error listing files in Approved folder: {res.text}")
    except Exception as e:
        print(f"[ZOHO] Exception listing files: {e}")
    return []

def get_empty_standby_airtable_records():
    """Fetch Airtable records in the view where Status is 'Standby' and Styled Photo is empty."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type":  "application/json",
    }
    # Filter for Status = 'Standby' and 'Styled Photo' is blank
    params = {
        "view":            AIRTABLE_VIEW,
        "filterByFormula": "AND({Status} = 'Standby', {Styled Photo} = BLANK())",
        "maxRecords":      100
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("records", [])
        else:
            print(f"[AIRTABLE] Error fetching records: {resp.text}")
    except Exception as e:
        print(f"[AIRTABLE] Exception fetching records: {e}")
    return []

def patch_airtable_record(record_id, share_link):
    """Attach the Zoho share link to the 'Styled Photo' field in Airtable."""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE}/{record_id}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type":  "application/json",
    }
    payload = {
        "fields": {
            "Styled Photo": [{"url": share_link}]
        }
    }
    try:
        resp = requests.patch(url, headers=headers, json=payload, timeout=15)
        return resp.status_code == 200
    except Exception as e:
        print(f"[AIRTABLE] Exception patching record {record_id}: {e}")
    return False

def main():
    print("[BATCH START] Fetching Zoho access token...")
    access_token = get_access_token()
    print("[ZOHO] Access token retrieved successfully.")
    
    print(f"\n[1] Listing approved files inside Zoho Chandelier Approved folder ('{CHANDELIER_APPROVED_FOLDER}')...")
    approved_files = get_zoho_approved_files(access_token)
    print(f"Found {len(approved_files)} approved files in Zoho.")
    
    if not approved_files:
        print("[BATCH DONE] No approved files found in Zoho Chandelier folder. Exiting.")
        return
        
    print("\n[2] Fetching empty Standby records from Airtable...")
    airtable_records = get_empty_standby_airtable_records()
    print(f"Found {len(airtable_records)} empty Standby records in Airtable.")
    
    if not airtable_records:
        print("[BATCH DONE] No empty Standby records available in Airtable. Exiting.")
        return
        
    print(f"\n[3] Starting batch attachment process (Max {min(len(approved_files), len(airtable_records))} operations)...")
    
    success_count = 0
    for idx, zoho_file in enumerate(approved_files):
        if idx >= len(airtable_records):
            print("\n[BATCH] Ran out of empty Airtable records. Stopping.")
            break
            
        record = airtable_records[idx]
        record_id = record.get("id")
        fields = record.get("fields", {})
        sku = fields.get("SKU Code", "N/A")
        item_name = fields.get("Item Name", "N/A")
        
        print(f"\nProcessing {idx+1}/{min(len(approved_files), len(airtable_records))}:")
        print(f"  Zoho File: {zoho_file['name']}")
        print(f"  Airtable : {sku} - {item_name}")
        
        # 1. Create Zoho public download link
        share_link = create_zoho_share_link(access_token, zoho_file["id"], zoho_file["name"])
        if not share_link:
            print("  [X] Failed to create Zoho share link. Skipping.")
            continue
            
        # 2. Patch Airtable record
        ok = patch_airtable_record(record_id, share_link)
        if ok:
            print(f"  [OK] Successfully attached photo to Airtable!")
            success_count += 1
        else:
            print(f"  [X] Failed to patch Airtable record.")
            
        time.sleep(0.5)  # Soft throttle to stay safe with Airtable rate limits
        
    print(f"\n[BATCH DONE] Successfully attached {success_count} approved photos to Airtable!")

if __name__ == "__main__":
    main()
