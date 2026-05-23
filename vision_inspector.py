import os
import base64
import requests
import json

LLM_API_URL = "http://127.0.0.1:1234/v1/chat/completions"
LLM_MODEL = "glm-4.6v-flash"

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

USER_PROMPT = "Analyze this image. Output your response ONLY as a valid JSON object matching the 'fields' defined in the system prompt. Do not include any conversational text or markdown formatting outside the JSON block."

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_prompt_for_category(category_or_path):
    cat = category_or_path.lower()
    if "pendant" in cat:
        return SYSTEM_PROMPT_PENDANT_LIGHT
    elif "floor" in cat:
        return SYSTEM_PROMPT_FLOOR_LAMP
    elif "bathroom" in cat or "painting" in cat:
        return SYSTEM_PROMPT_PAINTING_BATHROOM_LIGHTS
    elif "wall" in cat:
        return SYSTEM_PROMPT_WALL_LIGHTS
    elif "rechargeable" in cat:
        return SYSTEM_PROMPT_RECHARGEABLE_TABLE_LAMPS
    elif "table" in cat: # Note: "rechargeable table" matches rechargeable first
        return SYSTEM_PROMPT_TABLE_LAMPS
    elif "cluster" in cat:
        return SYSTEM_PROMPT_CLUSTER_CHANDELIERS
    elif "semi" in cat:
        return SYSTEM_PROMPT_SEMI_FLUSH_MOUNTED_LIGHTS
    elif "ceiling" in cat:
        return SYSTEM_PROMPT_CEILING_LIGHTS
    else:
        return SYSTEM_PROMPT # General / Chandelier

def test_vision(image_path, category=None):
    print(f"Encoding image: {image_path}")
    base64_image = encode_image_to_base64(image_path)
    
    resolve_key = category if category else image_path
    prompt = get_prompt_for_category(resolve_key)
    
    cat_info = prompt.get("target_category_matrix", prompt.get("target_category", {}))
    cat_name = cat_info.get("item_category", "General")
    print(f"Resolved prompt type for key '{resolve_key}': {cat_name}")
    
    # Let's read the suffix to set the mime type
    mime_type = "image/jpeg"
    if image_path.lower().endswith(".png"):
        mime_type = "image/png"
    elif image_path.lower().endswith(".webp"):
        mime_type = "image/webp"

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {
                "role": "system",
                "content": json.dumps(prompt, indent=2)
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": USER_PROMPT
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.1
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"Sending request to {LLM_API_URL} using model {LLM_MODEL}...")
    try:
        response = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=60)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print("--- LLM Output ---")
            print(content)
            print("------------------")
            
            try:
                parsed = json.loads(content.strip())
                print("Successfully parsed response JSON:")
                print(json.dumps(parsed, indent=2))
            except Exception as pe:
                print(f"JSON Parsing failed: {pe}")
        else:
            print(f"Error Response: {response.text}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    # Let's find one of the media files to test
    test_img = None
    local_raw = "./scraped_raw"
    if os.path.exists(local_raw):
        # Scan subdirectories recursively
        for root, dirs, files in os.walk(local_raw):
            for f in files:
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    test_img = os.path.join(root, f)
                    break
            if test_img:
                break

    if not test_img:
        # Fallback to brain folder
        media_dir = r"C:\Users\User\.gemini\antigravity\brain\48a498e6-62fb-44cd-9bec-a4edf2f9357f"
        if os.path.exists(media_dir):
            for f in os.listdir(media_dir):
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    test_img = os.path.join(media_dir, f)
                    break
            
    if test_img:
        print(f"Testing image: {test_img}")
        test_vision(test_img)
    else:
        print("No test image found.")
