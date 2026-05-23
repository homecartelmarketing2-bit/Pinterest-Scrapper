import os
import sys

# Ensure parent directory is in the path for proper imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scrape_and_upload import REQUIRED_FOLDERS, LOCAL_RAW_DIR, ZOHO_CATEGORY_FOLDERS

def main():
    print("[LOCAL START] Pre-structuring local scraped_raw directory...")
    print(f"Parent local raw directory: {LOCAL_RAW_DIR}")
    
    for term in REQUIRED_FOLDERS:
        # Map subfolders directly and exactly to Zoho folder names
        subfolder = ZOHO_CATEGORY_FOLDERS.get(term, term)
                
        category_raw_dir = os.path.join(LOCAL_RAW_DIR, subfolder)
        os.makedirs(category_raw_dir, exist_ok=True)
        print(f"  [CREATED] -> {subfolder}")
        
    print("[LOCAL DONE] All 10 category raw folders pre-created successfully!")

if __name__ == "__main__":
    main()
