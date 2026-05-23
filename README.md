# Pinterest Category Scraper & AI Quality Checker

An elite, production-grade automation pipeline designed to scrape Pinterest interior design images, execute strict multi-stage quality inspections using a local Vision LLM (GLM-4.6v-flash), dynamically manage folders in Zoho WorkDrive, and catalog outputs inside Airtable.

---

## 📂 Repository Structure

The project has been organized into a professional, industry-standard developer layout:

```text
├── 📂 archive/               # Legacy scripts (deprecated)
│   ├── scrape_home_feed.py
│   └── scrape_raw.py
├── 📂 data/                  # Persistent data storage (Pinterest profiles)
├── 📂 scraped_raw/           # Local download directories organized by category
│   ├── 📂 Chandelier/
│   ├── 📂 Floor Lamps/
│   ├── 📂 Pendant Lights/
│   └── 📂 ...
├── 📂 tests/                 # Development and delete testing utilities
│   ├── delete_validator.py
│   └── rename_validator.py
├── 📂 utils/                 # Admin, setup, and helper utilities
│   ├── create_approved_disregard_folders.py
│   ├── create_zoho_folders.py
│   ├── get_folders.py
│   ├── list_and_delete_files.py
│   └── upload_approved.py
├── 📝 prompts.py             # Core: 10 category-specific professional system prompts
├── 🚀 scrape_and_upload.py    # Main: Interactive CLI batch scraper & uploader
├── 🧪 vision_inspector.py      # Main: Granular local vision model testing harness
└── 📄 scraped_manifest.json  # Persistent manifest to prevent duplicate scrapes
```

---

## ⚙️ Architecture & Features

### 1. Granular Prompt Curation (`prompts.py`)
Houses 10 highly strict, sequential 9-step gatekeeping system prompts crafted to match **Architectural Digest** or high-end editorial standards. Each category incorporates precise, real-world interior design rules:
*   **Painting & Bathroom Lights**: Height (60-65" side sconces, 75-80" above-mirror bar), frame clearance, countertop clutter rejections.
*   **Wall Lights**: Sconce spacing (6-10 ft apart, staggered), bedside guidelines, and plain drywall rejections (requires paneled, brick, plaster, or lime-washed backdrops).
*   **Rechargeable Table Lamps**: Strictly **zero** visible wires/plugs/chargers, cozy evening centerpieces vignettes, and high-end design silhouettes.
*   **Table Lamps**: Bottom of shade at seated eye level to avoid glare, 1.5x lamp-to-table height ratio, and cord management rules.
*   **Cluster Chandeliers**: Dynamically staggered heights, 30-36" hanging height over islands, 7-foot walkthrough clearance.
*   **Semi Flush Mounted Lights**: 4-8" stem-lofted ceiling gap to project upward reflections, blocking flat dome "boob lights".
*   **Ceiling Lights**: Artistic statement branch/geometric structures set against molded or plaster ceilings.

### 2. Dynamic Zoho WorkDrive Resolution
No manual setup required. The main script automatically lists category subfolders inside your parent `"Lighting Fixtures"` folder (`1jvesd739f3203a31410096fd941bc9a1d52f`), detects whether the `"Approved"` and `"Disregard"` subfolders exist, and **creates them automatically** on the fly if they are missing.

### 3. Safety Locks & manifesting
*   **Playwright Browser Lock**: Safe single-instance scraping.
*   **Scraped Manifest Check**: Fully avoids repeating downloads of previously seen pins.
*   **Thread Limit Control**: Runs vision requests on a single worker thread to conserve local GPU memory and prevent LM Studio timeout stalls.

---

## 🚀 Getting Started

### 1. Install Dependencies
Ensure you have Python 3.10+ and the required packages installed:
```powershell
pip install requests playwright
playwright install
```

### 2. Perform Pinterest Authentication
To avoid bot detection and access Pinterest searches without roadblocks, run the manual login script:
```powershell
python scrape_and_upload.py --login
```
*Action: A visible browser window will open. Simply log into your Pinterest account manually, return to the terminal, and press `[ENTER]` to save your session.*

### 3. Run the Scraper & Checker
Launch the interactive terminal menu to start the automation:
```powershell
python scrape_and_upload.py
```
*Options:*
*   Select an individual category (1 to 10) or choose **A** to run all categories sequentially.
*   Choose if you want a **Fresh run** (overwriting history) or **Resume run** (resuming seamlessly).
*   Choose to run browser in **headless (hidden)** or **headful (visible)** mode.

### 4. Test the Vision Model Local Pipeline
Validate that your local LM Studio vision endpoint is running (`http://127.0.0.1:1234` with model `glm-4.6v-flash`) and execute the dynamic testing harness:
```powershell
python vision_inspector.py
```
*Note: This script will auto-detect your category based on the test image's name/path and run a full inspection test.*
