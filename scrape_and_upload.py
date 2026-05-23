import os
import urllib.parse
import json
import time
import requests
import tempfile
import random
import argparse
import threading
import base64
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Load local .env configurations if present ─────────────────
def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    parts = line.split("=", 1)
                    key = parts[0].strip()
                    val = parts[1].strip().strip('"').strip("'")
                    os.environ[key] = val

load_env()

# ─────────────────────────────────────────────
#  Playwright scraping constants & locks
# ─────────────────────────────────────────────
PINTEREST_PROFILE_DIR = os.path.join(os.getcwd(), "data", "pinterest_profile")
LOCAL_RAW_DIR         = r"C:\Users\User\Desktop\Pinterest Category Scraper\scraped_raw"
playwright_lock       = threading.Lock()

# ─────────────────────────────────────────────
#  Zoho credentials & config
# ─────────────────────────────────────────────
ZOHO_CLIENT_ID     = os.getenv("ZOHO_CLIENT_ID", "YOUR_ZOHO_CLIENT_ID")
ZOHO_CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET", "YOUR_ZOHO_CLIENT_SECRET")
ZOHO_REFRESH_TOKEN = os.getenv("ZOHO_REFRESH_TOKEN", "YOUR_ZOHO_REFRESH_TOKEN")
PARENT_FOLDER_ID   = "1jvesd739f3203a31410096fd941bc9a1d52f"
APPROVED_FOLDER_ID = "1jvesa9d41b8a1b104bebb415529d57e05d45"
REJECTED_FOLDER_ID = "jkt5qea09e4f7067f45f08215f97d3be460f2"

# ─────────────────────────────────────────────
#  LM Studio vision model (local)
# ─────────────────────────────────────────────
LLM_API_URL = "http://127.0.0.1:1234/v1/chat/completions"
LLM_MODEL   = "glm-4.6v-flash"

# ─────────────────────────────────────────────
#  Airtable credentials
# ─────────────────────────────────────────────
AIRTABLE_TOKEN   = os.getenv("AIRTABLE_TOKEN", "YOUR_AIRTABLE_TOKEN")
AIRTABLE_BASE_ID = "appSAnIy8QWSP2aZ9"
AIRTABLE_TABLE   = "tblDDmCs4S2ePxIfQ"
AIRTABLE_VIEW    = "viwdwB6Cu8gTT1QNC"

# ─────────────────────────────────────────────
#  Quality-checker prompts (imported from prompts.py)
# ─────────────────────────────────────────────
from prompts import (
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_PENDANT_LIGHT,
    SYSTEM_PROMPT_FLOOR_LAMP,
    SYSTEM_PROMPT_PAINTING_BATHROOM_LIGHTS,
    SYSTEM_PROMPT_WALL_LIGHTS,
    SYSTEM_PROMPT_RECHARGEABLE_TABLE_LAMPS,
    SYSTEM_PROMPT_TABLE_LAMPS,
    SYSTEM_PROMPT_CLUSTER_CHANDELIERS,
    SYSTEM_PROMPT_SEMI_FLUSH_MOUNTED_LIGHTS,
    SYSTEM_PROMPT_CEILING_LIGHTS
)

USER_PROMPT = (
    "Analyze this image. Output your response ONLY as a valid JSON object matching "
    "the 'fields' defined in the system prompt. Do not include any conversational "
    "text or markdown formatting outside the JSON block."
)

REQUIRED_FOLDERS = [
    "Architectural Digest sculptural Chandeliers",
    "High-end designer Pendant Lights moody",
    "Sculptural Ceiling Lights architectural digest",
    "Semi Flush Mounted Lights designer curated",
    "Cluster Chandeliers moody eclectic",
    "Designer Floor Lamps Architectural Digest",
    "Sculptural Table Lamps moody textures",
    "Rechargeable Table Lamps designer high-end",
    "Designer Wall Lights sculptural moody",
    "Painting & Bathroom Lights designer curated",
]

ZOHO_CATEGORY_FOLDERS = {
    "Architectural Digest sculptural Chandeliers": "Chandeliers",
    "High-end designer Pendant Lights moody": "Pendant Lights",
    "Sculptural Ceiling Lights architectural digest": "Ceiling Lights",
    "Semi Flush Mounted Lights designer curated": "Semi Flush Mounted Lights",
    "Cluster Chandeliers moody eclectic": "Cluster Chandeliers",
    "Designer Floor Lamps Architectural Digest": "Floor Lamps",
    "Sculptural Table Lamps moody textures": "Table Lamps",
    "Rechargeable Table Lamps designer high-end": "Rechargeable Table Lamps",
    "Designer Wall Lights sculptural moody": "Wall Lights",
    "Painting & Bathroom Lights designer curated": "Painting & Bathroom Lights",
}

MANIFEST_FILE  = "scraped_manifest.json"
manifest_lock  = threading.RLock()

# ─────────────────────────────────────────────
#  Manifest helpers
# ─────────────────────────────────────────────

def load_manifest():
    with manifest_lock:
        if os.path.exists(MANIFEST_FILE):
            try:
                with open(MANIFEST_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[MANIFEST] Error reading manifest: {e}. Starting fresh.")
        return {}

def save_manifest(manifest):
    with manifest_lock:
        try:
            with open(MANIFEST_FILE, "w") as f:
                json.dump(manifest, f, indent=4)
        except Exception as e:
            print(f"[MANIFEST] Error saving manifest: {e}")

def add_url_to_manifest(category, url):
    with manifest_lock:
        manifest = load_manifest()
        if category not in manifest:
            manifest[category] = []
        if url not in manifest[category]:
            manifest[category].append(url)
            save_manifest(manifest)

def clear_manifest_category(category):
    with manifest_lock:
        manifest = load_manifest()
        if category in manifest:
            manifest[category] = []
            save_manifest(manifest)

# ─────────────────────────────────────────────
#  Zoho helpers
# ─────────────────────────────────────────────

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

def get_or_create_folders(access_token):
    url = f"https://workdrive.zoho.com/api/v1/files/{PARENT_FOLDER_ID}/files"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Accept":        "application/vnd.api+json",
    }
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    data = res.json().get("data", [])

    existing_folders = {}
    for item in data:
        attrs = item.get("attributes", {})
        if attrs.get("type") == "folder":
            existing_folders[attrs.get("name")] = item.get("id")

    create_url    = "https://workdrive.zoho.com/api/v1/files"
    headers_post  = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Accept":        "application/vnd.api+json",
        "Content-Type":  "application/json",
    }

    folder_map = {}
    for name in REQUIRED_FOLDERS:
        if name in existing_folders:
            folder_map[name] = existing_folders[name]
            print(f"[FOLDER] Using existing folder '{name}' -> {folder_map[name]}")
        else:
            print(f"[CREATE] Creating folder '{name}'...")
            payload = {
                "data": {
                    "attributes": {"name": name, "parent_id": PARENT_FOLDER_ID},
                    "type":       "files",
                }
            }
            c_res = requests.post(create_url, headers=headers_post, json=payload)
            if c_res.status_code in (200, 201):
                f_id = c_res.json().get("data", {}).get("id")
                folder_map[name] = f_id
                print(f"[OK] Created folder '{name}' -> {f_id}")
            else:
                print(f"[ERROR] Failed to create folder '{name}': {c_res.text}")

    return folder_map

def get_existing_file_count(folder_id, access_token, term):
    prefix = term.replace(" ", "_") + "_"
    url    = f"https://workdrive.zoho.com/api/v1/files/{folder_id}/files"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Accept":        "application/vnd.api+json",
    }
    count = 0
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            for item in res.json().get("data", []):
                attrs = item.get("attributes", {})
                if attrs.get("type") == "file" and attrs.get("name", "").startswith(prefix):
                    count += 1
        else:
            print(f"[ERROR] Listing files in {folder_id}: {res.text}")
    except Exception as e:
        print(f"[ERROR] Listing files: {e}")
    return count

# Thread lock & cache for category subfolders
folder_resolution_lock = threading.Lock()
folder_resolution_cache = {} # Cache mapping term -> (approved_folder_id, disregard_folder_id)

def resolve_category_subfolders(access_token, term):
    """
    Dynamically resolve the category's folder under parent 'Lighting Fixtures',
    then check for subfolders 'Approved' and 'Disregard'.
    If missing, automatically create them under the category folder.
    Returns (approved_folder_id, disregard_folder_id).
    """
    global folder_resolution_cache
    
    with folder_resolution_lock:
        if term in folder_resolution_cache:
            return folder_resolution_cache[term]
        
        # 1. Get exact Zoho folder name from global mapping
        folder_name = ZOHO_CATEGORY_FOLDERS.get(term)
        if not folder_name:
            print(f"[DYNAMIC FOLDER] Unknown term mapping: '{term}'. Using fallback parent.")
            return APPROVED_FOLDER_ID, REJECTED_FOLDER_ID
            
        print(f"[DYNAMIC FOLDER] Resolving subfolders for category: '{folder_name}'...")
        
        # 2. Get the list of folders under parent to find the category folder ID
        list_url = f"https://workdrive.zoho.com/api/v1/files/{PARENT_FOLDER_ID}/files"
        headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}",
            "Accept":        "application/vnd.api+json",
        }
        
        category_folder_id = None
        try:
            res = requests.get(list_url, headers=headers, timeout=15)
            if res.status_code == 200:
                for item in res.json().get("data", []):
                    attrs = item.get("attributes", {})
                    if attrs.get("type") == "folder" and attrs.get("name") == folder_name:
                        category_folder_id = item.get("id")
                        break
            else:
                print(f"[DYNAMIC FOLDER] Error listing parent folders: {res.text}")
        except Exception as e:
            print(f"[DYNAMIC FOLDER] Exception listing parent folders: {e}")
            
        # Fallback: if category folder not found, create it under parent!
        if not category_folder_id:
            print(f"[DYNAMIC FOLDER] Category folder '{folder_name}' not found under parent. Creating it...")
            create_url = "https://workdrive.zoho.com/api/v1/files"
            payload = {
                "data": {
                    "attributes": {"name": folder_name, "parent_id": PARENT_FOLDER_ID},
                    "type":       "files",
                }
            }
            try:
                res = requests.post(create_url, headers={**headers, "Content-Type": "application/json"}, json=payload, timeout=15)
                if res.status_code in (200, 201):
                    category_folder_id = res.json().get("data", {}).get("id")
                    print(f"[DYNAMIC FOLDER] Created category folder '{folder_name}' -> {category_folder_id}")
                else:
                    print(f"[DYNAMIC FOLDER] Failed to create category folder '{folder_name}': {res.text}")
            except Exception as e:
                print(f"[DYNAMIC FOLDER] Exception creating category folder: {e}")
                
        if not category_folder_id:
            print(f"[DYNAMIC FOLDER] FAILED to resolve category folder ID. Using fallbacks.")
            return APPROVED_FOLDER_ID, REJECTED_FOLDER_ID
            
        # 3. Now list files/folders inside the category folder to find "Approved" and "Disregard"
        sub_list_url = f"https://workdrive.zoho.com/api/v1/files/{category_folder_id}/files"
        approved_id = None
        disregard_id = None
        
        try:
            res = requests.get(sub_list_url, headers=headers, timeout=15)
            if res.status_code == 200:
                for item in res.json().get("data", []):
                    attrs = item.get("attributes", {})
                    name_lower = attrs.get("name", "").strip().lower()
                    if attrs.get("type") == "folder":
                        if name_lower == "approved":
                            approved_id = item.get("id")
                        elif name_lower in ("disregard", "disregarded", "rejected"):
                            disregard_id = item.get("id")
            else:
                print(f"[DYNAMIC FOLDER] Error listing subfolders for '{folder_name}': {res.text}")
        except Exception as e:
            print(f"[DYNAMIC FOLDER] Exception listing subfolders for '{folder_name}': {e}")
            
        create_url = "https://workdrive.zoho.com/api/v1/files"
        
        # 4. Create "Approved" if missing
        if not approved_id:
            print(f"[DYNAMIC FOLDER] 'Approved' folder missing inside '{folder_name}'. Creating it...")
            payload = {
                "data": {
                    "attributes": {"name": "Approved", "parent_id": category_folder_id},
                    "type":       "files",
                }
            }
            try:
                res = requests.post(create_url, headers={**headers, "Content-Type": "application/json"}, json=payload, timeout=15)
                if res.status_code in (200, 201):
                    approved_id = res.json().get("data", {}).get("id")
                    print(f"[DYNAMIC FOLDER] Created 'Approved' subfolder -> {approved_id}")
                else:
                    print(f"[DYNAMIC FOLDER] Failed to create 'Approved' subfolder: {res.text}")
            except Exception as e:
                print(f"[DYNAMIC FOLDER] Exception creating 'Approved' subfolder: {e}")
                
        # 5. Create "Disregard" if missing
        if not disregard_id:
            print(f"[DYNAMIC FOLDER] 'Disregard' folder missing inside '{folder_name}'. Creating it...")
            payload = {
                "data": {
                    "attributes": {"name": "Disregard", "parent_id": category_folder_id},
                    "type":       "files",
                }
            }
            try:
                res = requests.post(create_url, headers={**headers, "Content-Type": "application/json"}, json=payload, timeout=15)
                if res.status_code in (200, 201):
                    disregard_id = res.json().get("data", {}).get("id")
                    print(f"[DYNAMIC FOLDER] Created 'Disregard' subfolder -> {disregard_id}")
                else:
                    print(f"[DYNAMIC FOLDER] Failed to create 'Disregard' subfolder: {res.text}")
            except Exception as e:
                print(f"[DYNAMIC FOLDER] Exception creating 'Disregard' subfolder: {e}")
                
        # Safe final fallbacks
        if not approved_id:
            approved_id = category_folder_id
        if not disregard_id:
            disregard_id = REJECTED_FOLDER_ID
            
        print(f"[DYNAMIC FOLDER] Resolved '{folder_name}': Approved -> {approved_id} | Disregard -> {disregard_id}")
        
        # Save to cache
        folder_resolution_cache[term] = (approved_id, disregard_id)
        return approved_id, disregard_id

# ─────────────────────────────────────────────
#  Airtable helpers
# ─────────────────────────────────────────────

def create_zoho_share_link(access_token, file_id, filename):
    """Create a public download link for a Zoho file."""
    url     = "https://workdrive.zoho.com/api/v1/links"
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type":  "application/json",
    }
    payload = {
        "data": {
            "attributes": {
                "resource_id":       file_id,
                "link_name":         filename,
                "request_user_data": False,
                "allow_download":    True,
                "role_id":           "34",
            },
            "type": "links",
        }
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code in (200, 201):
            dl_url = resp.json().get("data", {}).get("attributes", {}).get("download_url", "")
            if dl_url:
                return f"{dl_url}?directDownload=true"
        print(f"  [ZOHO LINK] Failed ({resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        print(f"  [ZOHO LINK] Error: {e}")
    return None


def get_standby_records(n=5):
    """Fetch up to N Standby Airtable records from the view."""
    url     = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type":  "application/json",
    }
    params = {
        "view":            AIRTABLE_VIEW,
        "filterByFormula": "AND({Status} = 'Standby', {Reference Photo} = BLANK(), {Styled Photo Prompt} = BLANK())",
        "maxRecords":      n,
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json().get("records", [])
    except Exception as e:
        print(f"  [AIRTABLE] Error fetching standby records: {e}")
    return []


def update_airtable_record(record_id, fields_dict):
    """PATCH a single Airtable record with the given fields."""
    url     = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE}/{record_id}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type":  "application/json",
    }
    try:
        resp = requests.patch(url, headers=headers, json={"fields": fields_dict}, timeout=15)
        return resp.status_code == 200
    except Exception as e:
        print(f"  [AIRTABLE] Patch error: {e}")
    return False


def get_airtable_attached_filenames():
    """Retrieve a set of all filenames currently attached to 'Reference Photo' in Airtable."""
    url     = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
        "Content-Type":  "application/json",
    }
    filenames = set()
    offset = None
    
    try:
        while True:
            params = {
                "view": AIRTABLE_VIEW,
                "fields": ["Reference Photo"],
                "maxRecords": 100
            }
            if offset:
                params["offset"] = offset
                
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            if resp.status_code != 200:
                print(f"  [AIRTABLE] Error fetching attached filenames: {resp.text}")
                break
                
            data = resp.json()
            for record in data.get("records", []):
                attachments = record.get("fields", {}).get("Reference Photo", [])
                if isinstance(attachments, list):
                    for att in attachments:
                        fn = att.get("filename")
                        if fn:
                            filenames.add(fn)
                            
            offset = data.get("offset")
            if not offset:
                break
                
    except Exception as e:
        print(f"  [AIRTABLE] Exception fetching attached filenames: {e}")
        
    return filenames


def get_zoho_approved_files(access_token, folder_id):
    """List all files in the given Approved folder in Zoho WorkDrive, sorted newest to oldest."""
    url = f"https://workdrive.zoho.com/api/v1/files/{folder_id}/files"
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


def generate_all_prompts(image_bytes: bytes, mime: str, retries: int = 3) -> list[str] | None:
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    
    system_prompt = (
        "You are a world-class premium room interior designer. "
        "Your job is to analyze the provided reference photo and write exactly 5 distinct, highly detailed prompts that will generate PURE interior room photography. "
        "CRITICAL RULES: "
        "1. The generated image must be a PURE PHOTOGRAPH of a beautiful interior room — absolutely NO text, NO labels, NO watermarks, NO titles, NO captions, NO overlays of any kind. "
        "2. Describe the room scene in vivid detail: the room type (living room, dining room, bedroom, foyer, etc.), the hero light fixture (its shape, materials, glow, hanging style), "
        "the surrounding furniture and decor, wall treatments, flooring, color palette, spatial layout, natural or artificial lighting quality, and the overall mood/atmosphere. "
        "3. Each prompt must describe a complete, photorealistic interior room scene — as if photographed for Architectural Digest magazine. "
        "4. Do NOT mention any brand names, product codes, or text elements. Focus purely on visual description of the space.\n\n"
        "Return ONLY a valid JSON object with a single key 'prompts' containing a list of exactly 5 prompt strings. No extra text or markdown."
    )

    user_prompt = (
        "Look at this reference photo carefully. Based on the light fixture and interior style you see, write 5 different detailed interior room photography prompts:\n"
        "1. Faithfully describe this exact room scene — the layout, materials, colors, fixture details, furniture, and lighting atmosphere. End with: 'photorealistic interior photography, Architectural Digest style, 8K.'\n"
        "2. A different room type or angle featuring the same style of light fixture — for example, a wide-angle view of a luxurious dining room or a cozy reading nook. Same photorealistic quality.\n"
        "3. The same room but in evening ambiance — warm golden glow from the fixture, soft shadows, intimate sophisticated atmosphere.\n"
        "4. Same fixture style but in a completely different interior design theme — for example, modern minimalist, art deco, Scandinavian, industrial chic, or Mediterranean villa.\n"
        "5. A dramatic editorial cover-worthy shot — cinematic lighting, rich textures, deep contrasts, and stunning spatial composition.\n\n"
        "IMPORTANT: Every prompt must describe ONLY a visual interior room scene. NO text, NO labels, NO watermarks in the image. Pure photography only.\n\n"
        "Output ONLY a valid JSON object:\n"
        "{\n"
        "  \"prompts\": [\n"
        "    \"Prompt 1...\",\n"
        "    \"Prompt 2...\",\n"
        "    \"Prompt 3...\",\n"
        "    \"Prompt 4...\",\n"
        "    \"Prompt 5...\"\n"
        "  ]\n"
        "}"
    )

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text",      "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            },
        ],
        "temperature": 0.7
    }

    for attempt in range(1, retries + 2):
        try:
            print(f"    [PROMPT GEN] Sending single-call request to LM Studio (attempt {attempt})...")
            resp = requests.post(
                LLM_API_URL,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=300,
            )
            if resp.status_code != 200:
                print(f"    [PROMPT GEN] HTTP {resp.status_code} (attempt {attempt}): {resp.text[:200]}")
                continue

            content = resp.json()["choices"][0]["message"]["content"].strip()
            # Strip markdown fences if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            parsed = json.loads(content)
            prompts = parsed.get("prompts", [])
            if isinstance(prompts, list) and len(prompts) == 5:
                return prompts
            else:
                print(f"    [PROMPT GEN] Invalid format or length of prompts list: {len(prompts)} items.")
        except Exception as e:
            print(f"    [PROMPT GEN] Request failed on attempt {attempt}: {e}")
            if attempt <= retries:
                time.sleep(3)
    return None

def push_photo_and_prompts(access_token, file_id, filename, image_bytes, mime, category):
    """
    After a photo is approved and uploaded to Zoho:
      - Generate 5 variations in a single LLM request
      - Push the results to Airtable sequentially
    """
    # ── Step 1: Zoho share link ──────────────────────────────────────────
    share_url = create_zoho_share_link(access_token, file_id, filename)
    if not share_url:
        print(f"  [AIRTABLE] Could not create Zoho share link — skipping.")
        return False

    # ── Step 2: Fetch 5 Standby records upfront (1 API call) ────────────
    records = get_standby_records(n=5)
    if not records:
        print(f"  [AIRTABLE] No Standby records available — skipping.")
        return False

    print(f"\n  [PROMPT GEN] Generating 5 prompt variations in a single local LLM call...")
    prompts = generate_all_prompts(image_bytes, mime)

    if not prompts:
        print(f"  [PROMPT GEN] [WARNING] Single-call prompt generation failed. Skipping this image for Airtable upload to avoid generic fallbacks.")
        return False

    # ── Step 3: Insert variations to Airtable ────────────────────────────
    print(f"  [AIRTABLE] Inserting variations to Airtable...")
    for i, record in enumerate(records):
        record_id = record.get("id")
        fields    = record.get("fields", {})
        sku       = fields.get("SKU Code", "N/A")
        item_name = fields.get("Item Name", "N/A")
        
        prompt = prompts[i]

        patch = {}
        if i == 0:
            patch["Reference Photo"] = [{"url": share_url}]   # photo only on row 1
        if prompt:
            patch["Styled Photo Prompt"] = prompt

        if patch:
            ok = update_airtable_record(record_id, patch)
            label = "Photo + Prompt" if i == 0 else "Prompt only"
            if ok:
                print(f"    [AIRTABLE] [OK] Inserted ({label} - Var {i+1}) -> {sku} - {item_name}")
                print(f"      -> {prompt[:110]}...")
            else:
                print(f"    [AIRTABLE] [X] Insert failed -> {sku}")

        time.sleep(0.2)
    return True


# ─────────────────────────────────────────────
#  LLM vision quality checker
# ─────────────────────────────────────────────

def llm_check_image(image_bytes: bytes, mime_type: str = "image/jpeg", term: str = None, retries: int = 3) -> dict | None:
    """
    Send image bytes to the local LM Studio vision model.
    Returns parsed JSON dict from the model, or None on failure.
    Expected keys: what_i_see, failed_step, aesthetic_score, is_beautiful, reason
    """
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    prompt = SYSTEM_PROMPT
    if term == "High-end designer Pendant Lights moody":
        prompt = SYSTEM_PROMPT_PENDANT_LIGHT
    elif term == "Designer Floor Lamps Architectural Digest":
        prompt = SYSTEM_PROMPT_FLOOR_LAMP
    elif term == "Painting & Bathroom Lights designer curated":
        prompt = SYSTEM_PROMPT_PAINTING_BATHROOM_LIGHTS
    elif term == "Designer Wall Lights sculptural moody":
        prompt = SYSTEM_PROMPT_WALL_LIGHTS
    elif term == "Rechargeable Table Lamps designer high-end":
        prompt = SYSTEM_PROMPT_RECHARGEABLE_TABLE_LAMPS
    elif term == "Sculptural Table Lamps moody textures":
        prompt = SYSTEM_PROMPT_TABLE_LAMPS
    elif term == "Cluster Chandeliers moody eclectic":
        prompt = SYSTEM_PROMPT_CLUSTER_CHANDELIERS
    elif term == "Semi Flush Mounted Lights designer curated":
        prompt = SYSTEM_PROMPT_SEMI_FLUSH_MOUNTED_LIGHTS
    elif term == "Sculptural Ceiling Lights architectural digest":
        prompt = SYSTEM_PROMPT_CEILING_LIGHTS
    elif term == "Architectural Digest sculptural Chandeliers":
        prompt = SYSTEM_PROMPT

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role":    "system",
                "content": json.dumps(prompt, indent=2),
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": USER_PROMPT},
                    {
                        "type":      "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                    },
                ],
            },
        ],
        "temperature": 0.1,
    }

    for attempt in range(1, retries + 2):
        try:
            resp = requests.post(
                LLM_API_URL,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=400,
            )
            if resp.status_code != 200:
                print(f"  [LLM] HTTP {resp.status_code} (attempt {attempt}): {resp.text[:200]}")
                if attempt <= retries:
                    print(f"  [LLM] Retrying after HTTP failure…")
                    time.sleep(5)
                continue

            content = resp.json()["choices"][0]["message"]["content"].strip()

            # Strip markdown fences if model added them anyway
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            return json.loads(content)

        except json.JSONDecodeError as e:
            print(f"  [LLM] JSON parse error on attempt {attempt}: {e}")
            if attempt <= retries:
                print(f"  [LLM] Retrying after JSON parse error…")
                time.sleep(5)
        except Exception as e:
            print(f"  [LLM] Request error on attempt {attempt}: {e}")
            if attempt <= retries:
                print(f"  [LLM] Retrying after request error…")
                time.sleep(5)

    return None

# ─────────────────────────────────────────────
#  Pinterest scraper
# ─────────────────────────────────────────────

def _best_src(src: str, srcset: str) -> str:
    choices = []
    for part in srcset.split(","):
        bits = part.strip().split()
        if not bits:
            continue
        width = 0
        if len(bits) > 1 and bits[1].endswith("w"):
            try:
                width = int(bits[1][:-1])
            except ValueError:
                width = 0
        choices.append((width, bits[0]))
    if choices:
        return max(choices, key=lambda item: item[0])[1]
    return src

def _is_usable_pinimg_url(url: str, width: int, height: int) -> bool:
    if not url or "pinimg.com" not in url:
        return False
    if any(part in url.lower() for part in ("/avatars/", "/rs/", "75x75")):
        return False
    return width >= 120 and height >= 120

def _extract_image_urls(page) -> list[str]:
    try:
        items = page.locator("img").evaluate_all(
            """imgs => imgs.map(img => ({
                src: img.currentSrc || img.src || "",
                srcset: img.getAttribute("srcset") || "",
                width: img.naturalWidth || 0,
                height: img.naturalHeight || 0
            }))"""
        )
    except Exception as e:
        print(f"  [PLAYWRIGHT] Error evaluating img elements: {e}")
        return []

    urls = []
    for item in items:
        url = _best_src(item.get("src", ""), item.get("srcset", ""))
        if _is_usable_pinimg_url(url, item.get("width", 0), item.get("height", 0)):
            upgraded = re.sub(r"/\d+x/", "/originals/", url)
            urls.append(upgraded)
    return list(dict.fromkeys(urls))

def get_search_query(term: str) -> str:
    # Map each required folder to a clean, simple search keyword ending with "room interior design"
    mapping = {
        "Architectural Digest sculptural Chandeliers": "chandelier room interior design",
        "High-end designer Pendant Lights moody": "pendant light room interior design",
        "Sculptural Ceiling Lights architectural digest": "ceiling light room interior design",
        "Semi Flush Mounted Lights designer curated": "semi flush mount light room interior design",
        "Cluster Chandeliers moody eclectic": "chandelier room interior design",
        "Designer Floor Lamps Architectural Digest": "floor lamp room interior design",
        "Sculptural Table Lamps moody textures": "table lamp room interior design",
        "Rechargeable Table Lamps designer high-end": "rechargeable table lamp room interior design",
        "Designer Wall Lights sculptural moody": "wall light room interior design",
        "Painting & Bathroom Lights designer curated": "bathroom light room interior design",
    }
    return mapping.get(term, f"{term} room interior design")

def scrape_pinterest_images_playwright(term, limit=30, seen_urls=None, headless=True):
    from playwright.sync_api import sync_playwright
    search_query = get_search_query(term)
    print(f"[{term}] Scraping Pinterest (Playwright) for '{search_query}' (need {limit} candidates)...")
    
    candidates = []
    seen_images = set(seen_urls) if seen_urls else set()
    
    try:
        with sync_playwright() as p:
            launch_kwargs = {
                "headless": headless,
                "viewport": {"width": 1365, "height": 900},
                "args": ["--disable-blink-features=AutomationControlled"],
            }
            context = p.chromium.launch_persistent_context(
                user_data_dir=PINTEREST_PROFILE_DIR,
                **launch_kwargs,
            )
            page = context.pages[0] if context.pages else context.new_page()

            search_url = f"https://www.pinterest.com/search/pins/?q={urllib.parse.quote(search_query)}"
            page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)

            max_scrolls = 20
            for scroll in range(max_scrolls):
                extracted = _extract_image_urls(page)
                page_added = 0
                for img_url in extracted:
                    if img_url not in seen_images:
                        seen_images.add(img_url)
                        candidates.append(img_url)
                        page_added += 1

                if page_added > 0:
                    print(f"[{term}] Scroll {scroll+1}: +{page_added} candidates -> {len(candidates)} total.")

                if len(candidates) >= limit:
                    break

                page.mouse.wheel(0, 2400)
                page.wait_for_timeout(1500)

            context.close()
    except Exception as e:
        print(f"[{term}] Playwright scraping error: {e}")
        
    return candidates[:limit]

# ─────────────────────────────────────────────
#  Per-category worker
# ─────────────────────────────────────────────

def worker(term, folder_id, access_token, fresh=False, headless=True):
    try:
        # Dynamically resolve approved and rejected folder IDs for the category
        folder_id, rejected_folder_id = resolve_category_subfolders(access_token, term)

        # Resolve clean subfolder name under scraped_raw using the exact Zoho category folder name
        subfolder = ZOHO_CATEGORY_FOLDERS.get(term, term)

        category_raw_dir = os.path.join(LOCAL_RAW_DIR, subfolder)
        os.makedirs(category_raw_dir, exist_ok=True)

        # ─────────────────────────────────────────────────────────────
        #  BACKLOG CHECK: Process existing Zoho approved files first
        # ─────────────────────────────────────────────────────────────
        print(f"\n[{term}] Checking Zoho Approved backlog before scraping...")
        approved_files = get_zoho_approved_files(access_token, folder_id)
        if approved_files:
            print(f"[{term}] Found {len(approved_files)} approved files in Zoho.")
            
            # Fetch already-attached filenames in Airtable to avoid duplication
            attached_filenames = get_airtable_attached_filenames()
            print(f"[{term}] Found {len(attached_filenames)} attached filenames in Airtable.")
            
            # Filter files that are in Zoho Approved but NOT in Airtable
            backlog_files = [f for f in approved_files if f["name"] not in attached_filenames]
            
            if backlog_files:
                print(f"[{term}] Found {len(backlog_files)} files in Zoho Approved backlog that need to be attached to Airtable: {[f['name'] for f in backlog_files]}")
                for idx, zoho_file in enumerate(backlog_files):
                    filename = zoho_file["name"]
                    print(f"\n  [BACKLOG] Processing file {idx+1}/{len(backlog_files)}: {filename}")
                    
                    # 1. Download image bytes
                    image_bytes = download_zoho_file(access_token, zoho_file["id"], filename)
                    if not image_bytes:
                        print(f"  [BACKLOG] Download failed for {filename} — skipping.")
                        continue
                        
                    # 2. Determine MIME type
                    lower_name = filename.lower()
                    if ".png" in lower_name:
                        mime = "image/png"
                    elif ".webp" in lower_name:
                        mime = "image/webp"
                    else:
                        mime = "image/jpeg"
                        
                    # 3. Push to Airtable and generate prompts
                    try:
                        push_photo_and_prompts(
                            access_token=access_token,
                            file_id=zoho_file["id"],
                            filename=filename,
                            image_bytes=image_bytes,
                            mime=mime,
                            category=term
                        )
                    except Exception as e:
                        print(f"  [BACKLOG] [ERROR] Pushing to Airtable: {e}")
                        
                    time.sleep(1.0)
            else:
                print(f"[{term}] Zoho Approved backlog is completely synced with Airtable. Proceeding...")
        else:
            print(f"[{term}] No files found in Zoho Approved folder.")
        # ─────────────────────────────────────────────────────────────

        if fresh:
            clear_manifest_category(term)
            existing_count = 0
        else:
            existing_count = get_existing_file_count(folder_id, access_token, term)
            print(f"[{term}] {existing_count} existing files in Zoho.")

        if existing_count >= 30:
            print(f"[{term}] Already at 30 - skipping.")
            return

        needed = 30 - existing_count

        # Load manifest to skip already-seen URLs
        manifest = load_manifest()
        seen_urls = set(manifest.get(term, []))

        # Download exactly 30 candidate raw images to the local scraped_raw directory first
        local_saved_files = [] # list of dicts: {"local_path": str, "url": str, "ext": str, "mime": str}
        attempts = 0

        while len(local_saved_files) < 30 and attempts < 3:
            attempts += 1
            remaining_to_download = 30 - len(local_saved_files)
            fetch_n = max(remaining_to_download * 2, 15)

            print(f"[{term}] Scraper attempt {attempts}: fetching {fetch_n} candidates from Pinterest...")
            with playwright_lock:
                candidates = scrape_pinterest_images_playwright(
                    term, limit=fetch_n, seen_urls=seen_urls, headless=headless
                )

            if not candidates:
                print(f"[{term}] No more candidates from Pinterest search - breaking.")
                break

            for img_url in candidates:
                seen_urls.add(img_url)
                add_url_to_manifest(term, img_url)

                if len(local_saved_files) >= 30:
                    break

                # Download image
                try:
                    img_resp = requests.get(img_url, timeout=15)
                    if img_resp.status_code != 200:
                        print(f"[{term}] Download failed ({img_resp.status_code}) for: {img_url}")
                        continue
                    image_bytes = img_resp.content
                except Exception as e:
                    print(f"[{term}] Download error for {img_url}: {e}")
                    continue

                # Determine extension & mime
                lower_url = img_url.lower()
                if ".png" in lower_url:
                    mime = "image/png"
                    ext  = ".png"
                elif ".webp" in lower_url:
                    mime = "image/webp"
                    ext  = ".webp"
                else:
                    mime = "image/jpeg"
                    ext  = ".jpg"

                # Save to local scraped_raw category directory
                timestamp = int(time.time())
                rand_id = random.randint(1000, 9999)
                local_filename = f"{term.replace(' ', '_')}_raw_{timestamp}_{len(local_saved_files) + 1}_{rand_id}{ext}"
                local_path = os.path.join(category_raw_dir, local_filename)

                try:
                    with open(local_path, "wb") as f:
                        f.write(image_bytes)
                    print(f"[{term}] Saved raw local file ({len(local_saved_files) + 1}/30): {local_filename}")
                    local_saved_files.append({
                        "local_path": local_path,
                        "url": img_url,
                        "ext": ext,
                        "mime": mime
                    })
                except Exception as e:
                    print(f"[{term}] Error saving local file {local_filename}: {e}")

                if len(local_saved_files) >= 30:
                    break

        if not local_saved_files:
            print(f"[{term}] No local raw images successfully saved. Exiting worker.")
            return

        # Now, process each downloaded local file with LLM and upload to Zoho
        print(f"\n[{term}] Completed local saving of {len(local_saved_files)} files. Starting LLM checks and Zoho uploads...")

        checked          = 0
        approved         = 0
        rejected         = 0
        rejected_reasons = []
        file_index       = existing_count + 1   # Approved file name counter

        for item in local_saved_files:
            local_path = item["local_path"]
            mime = item["mime"]
            ext = item["ext"]

            # Read image bytes from local file
            try:
                with open(local_path, "rb") as f:
                    image_bytes = f.read()
            except Exception as e:
                print(f"[{term}] Error reading local file {local_path}: {e} - skipping.")
                continue

            # LLM quality check
            print(f"[{term}] Checking image {checked + 1}/{len(local_saved_files)} with LLM...")
            result = llm_check_image(image_bytes, mime, term=term)
            checked += 1

            if result is None:
                print(f"  [LLM] No response - skipping image.")
                rejected += 1
                continue

            score      = result.get("aesthetic_score", 0)
            beautiful  = result.get("is_beautiful", False)
            if isinstance(beautiful, str):
                beautiful = beautiful.lower() == "true"

            failed_step = result.get("failed_step", "Unknown")
            reason      = result.get("reason", "")
            what_i_see  = result.get("what_i_see", "")

            print(f"  Scene : {what_i_see}")
            print(f"  Score : {score}/10 | Failed: {failed_step} | Beautiful: {beautiful}")
            print(f"  Reason: {reason}")

            if not beautiful:
                rejected += 1
                rejected_reasons.append(f"  [X] [{failed_step}] score={score} - {reason}")
                print(f"  -> REJECTED")

                # Upload to Zoho rejected folder
                rejected_filename = f"{term.replace(' ', '_')}_rejected_{int(time.time())}_{random.randint(1000, 9999)}{ext}"
                try:
                    with open(local_path, "rb") as f:
                        upload_resp = requests.post(
                            "https://workdrive.zoho.com/api/v1/upload",
                            headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
                            files={"content": (rejected_filename, f)},
                            data={"parent_id": rejected_folder_id, "override-name-exist": "true"},
                        )
                    if upload_resp.status_code in (200, 201):
                        print(f"  -> UPLOADED REJECTED IMAGE: {rejected_filename}")
                    else:
                        print(f"  [REJECTED UPLOAD] Failed to upload {rejected_filename}: {upload_resp.text[:200]}")
                except Exception as e:
                    print(f"  [REJECTED UPLOAD] Exception during upload of {rejected_filename}: {e}")

                continue

            # Upload to Approved folder in Zoho
            filename = f"{term.replace(' ', '_')}_{file_index}{ext}"
            try:
                with open(local_path, "rb") as f:
                    upload_resp = requests.post(
                        "https://workdrive.zoho.com/api/v1/upload",
                        headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
                        files={"content": (filename, f)},
                        data={"parent_id": folder_id, "override-name-exist": "true"},
                    )
                if upload_resp.status_code in (200, 201):
                    approved += 1
                    file_index += 1
                    print(f"  -> APPROVED & UPLOADED ({approved} new approved): {filename}")
                    
                    # ── Push to Airtable ──
                    try:
                        resp_json = upload_resp.json()
                        data_list = resp_json.get("data", [])
                        if data_list:
                            file_id = data_list[0].get("attributes", {}).get("resource_id")
                            if file_id:
                                print(f"  [AIRTABLE] Launching push pipeline for {filename}...")
                                push_photo_and_prompts(access_token, file_id, filename, image_bytes, mime, term)
                            else:
                                print(f"  [AIRTABLE] [WARNING] Could not find resource_id in upload response: {resp_json}")
                        else:
                            print(f"  [AIRTABLE] [WARNING] Empty data in upload response: {resp_json}")
                    except Exception as e:
                        print(f"  [AIRTABLE] [ERROR] Parsing upload response or pushing to Airtable: {e}")
                else:
                    print(f"  [UPLOAD] Failed {filename}: {upload_resp.text[:200]}")
            except Exception as e:
                print(f"  [UPLOAD] Exception during upload of {filename}: {e}")

            time.sleep(random.uniform(0.3, 0.8))

        # == Summary ======================================================
        print(f"\n{'-'*55}")
        print(f"[{term}] DONE - checked {checked}, approved {approved}, rejected {rejected}")
        if rejected_reasons:
            print(f"[{term}] Rejection log:")
            for r in rejected_reasons[-10:]:   # show last 10 to keep log tidy
                print(r)
        print(f"{'-'*55}\n")

    except Exception as e:
        print(f"[{term}] Worker crashed: {e}")

# ─────────────────────────────────────────────
#  Manual Pinterest login flow
# ─────────────────────────────────────────────

def pinterest_login_flow():
    from playwright.sync_api import sync_playwright
    print(f"[LOGIN] Starting Playwright in visible mode to perform Pinterest login...")
    print(f"[LOGIN] Profile directory: {PINTEREST_PROFILE_DIR}")
    
    try:
        with sync_playwright() as p:
            launch_kwargs = {
                "headless": False,
                "viewport": {"width": 1365, "height": 900},
                "args": ["--disable-blink-features=AutomationControlled"],
            }
            context = p.chromium.launch_persistent_context(
                user_data_dir=PINTEREST_PROFILE_DIR,
                **launch_kwargs,
            )
            page = context.pages[0] if context.pages else context.new_page()

            print(f"[LOGIN] Navigating to Pinterest...")
            page.goto("https://www.pinterest.com/", wait_until="domcontentloaded", timeout=60000)
            
            print("\n" + "=" * 80)
            print("  [ACTION REQUIRED] PLEASE LOG INTO PINTEREST MANUALLY IN THE OPEN BROWSER WINDOW.")
            print("  Once you are fully logged in and see your home feed, come back to this")
            print("  terminal and press [ENTER] to save your session and close the browser.")
            print("=" * 80 + "\n")
            
            input("Press [ENTER] to continue after logging in...")
            
            print("[LOGIN] Saving persistent session and closing context...")
            context.close()
            print("[LOGIN] Success! Session saved to profile directory.")
    except Exception as e:
        print(f"[LOGIN] Error during manual login flow: {e}")

# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Pinterest Scraper -> LLM Quality Check -> Zoho WorkDrive"
    )
    parser.add_argument(
        "--fresh", action="store_true",
        help="Clear manifest and overwrite existing files (start from scratch)"
    )
    parser.add_argument(
        "--category", type=str, default=None,
        help="Run only for this one category (exact name, case-sensitive)"
    )
    parser.add_argument(
        "--login", action="store_true",
        help="Launch visible browser to perform manual Pinterest login"
    )
    parser.add_argument(
        "--no-headless", action="store_true",
        help="Run Playwright scraping batches in visible browser window"
    )
    args = parser.parse_args()

    fresh_run = args.fresh
    no_headless = args.no_headless
    target_folders = []

    # Check if run interactively (no arguments passed)
    import sys
    is_interactive = len(sys.argv) == 1

    if is_interactive:
        print("\n" + "=" * 70)
        print("          PINTEREST SCRAPER & AI QUALITY CHECKER MENU")
        print("=" * 70)
        print("Select a category to scrape and check:")
        for idx, cat in enumerate(REQUIRED_FOLDERS, 1):
            clean_name = ZOHO_CATEGORY_FOLDERS.get(cat, cat)
            print(f"  [{idx}] {clean_name}")
        print("\n  [A] Run All Categories Sequentially")
        print("  [L] Pinterest Login (Launch visible browser to log in)")
        print("  [Q] Quit")
        print("=" * 70)
        
        choice = input("Enter your choice (1-10, A, L, or Q): ").strip().upper()
        
        if choice == "Q":
            print("Exiting.")
            return
        elif choice == "L":
            pinterest_login_flow()
            return
        elif choice == "A":
            target_folders = REQUIRED_FOLDERS
        else:
            try:
                num = int(choice)
                if 1 <= num <= len(REQUIRED_FOLDERS):
                    target_folders = [REQUIRED_FOLDERS[num - 1]]
                else:
                    print("Invalid number choice. Exiting.")
                    return
            except ValueError:
                print("Invalid input. Exiting.")
                return

        # Ask for fresh run in interactive mode
        fresh_input = input("\nDo you want a FRESH run? (Clears history for this category) (y/N): ").strip().lower()
        fresh_run = fresh_input in ("y", "yes")

        # Ask for headless mode in interactive mode
        headless_input = input("Run browser in headless (hidden) mode? (Y/n): ").strip().lower()
        no_headless = headless_input in ("n", "no")
    else:
        # Command line arguments usage
        if args.login:
            pinterest_login_flow()
            return
        
        target_folders = (
            [args.category] if args.category and args.category in REQUIRED_FOLDERS
            else REQUIRED_FOLDERS
        )

    print(f"\n[MAIN] Starting run: fresh={fresh_run} | headless={not no_headless} | categories={len(target_folders)}")
    for fld in target_folders:
        print(f"  -> {fld}")
    print()

    access_token = get_access_token()
    print("[MAIN] Access token OK.")

    folder_map = {term: APPROVED_FOLDER_ID for term in REQUIRED_FOLDERS}
    print("[MAIN] Folder map set directly to flat Approved folder.")

    with ThreadPoolExecutor(max_workers=1) as executor:   # Set to 1 so only 1 photo/category is checked at a time (saves local GPU memory and prevents stalls)
        futures = {
            executor.submit(worker, term, folder_map[term], access_token, fresh_run, not no_headless): term
            for term in target_folders
            if term in folder_map
        }
        for future in as_completed(futures):
            term = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"[MAIN] {term} raised: {e}")

    print("[MAIN] All done!")

if __name__ == "__main__":
    main()
