import os
import json
import requests
import urllib.parse
import time
import random

def scrape_pinterest_images(search_query, limit=15):
    print(f"Scraping Pinterest for: '{search_query}' (limit: {limit})")
    candidates = []
    seen_images = set()
    bookmarks = [""]

    headers = {
        "User-Agent":              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "X-Pinterest-AppState":    "active",
        "X-Pinterest-Source-Url":  f"/search/pins/?q={urllib.parse.quote(search_query)}",
        "X-Pinterest-PWS-Handler": "www/search/pins.js",
        "X-Requested-With":        "XMLHttpRequest",
        "Accept":                  "application/json, text/javascript, */*; q=0.01",
        "Accept-Language":         "en-US,en;q=0.9",
        "Referer":                 "https://www.pinterest.com/",
    }

    while len(candidates) < limit:
        args = {
            "options": {"query": search_query, "bookmarks": bookmarks},
            "context": {},
        }
        url = (
            "https://www.pinterest.com/resource/BaseSearchResource/get/"
            f"?data={urllib.parse.quote(json.dumps(args))}"
        )

        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"Pinterest returned {response.status_code} — stopping.")
                break

            resource_response = response.json().get("resource_response", {})
            data_list         = resource_response.get("data", [])

            results = (
                data_list if isinstance(data_list, list)
                else data_list.get("results", [])
            )
            if not results:
                print(f"No more results.")
                break

            for item in results:
                if not isinstance(item, dict): continue
                images = item.get("images")
                if not isinstance(images, dict): continue
                for size in ["originals", "736x", "600x", "474x"]:
                    if size in images and isinstance(images[size], dict):
                        img_url = images[size].get("url")
                        if img_url and img_url not in seen_images:
                            seen_images.add(img_url)
                            candidates.append(img_url)
                            break
            
            if len(candidates) >= limit: break

            next_bookmark = resource_response.get("bookmark")
            if next_bookmark and next_bookmark != bookmarks[0]:
                bookmarks = [next_bookmark]
            else:
                break
            time.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            print(f"Scrape error: {e}")
            break

    return candidates[:limit]

def main():
    category = "Architectural Digest sculptural chandelier" # More specific
    output_dir = "scraped_raw_v2"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    urls = scrape_pinterest_images(category, limit=15)
    print(f"Found {len(urls)} images. Starting download...")

    for i, url in enumerate(urls):
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                ext = ".jpg"
                if ".png" in url.lower(): ext = ".png"
                elif ".webp" in url.lower(): ext = ".webp"
                
                filename = f"scraped_{i}{ext}"
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                print(f"  Downloaded: {filename}")
            else:
                print(f"  Failed: {url}")
        except Exception as e:
            print(f"  Error downloading {url}: {e}")

if __name__ == "__main__":
    main()
