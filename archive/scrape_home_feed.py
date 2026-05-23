import os
import json
import requests
import urllib.parse
import time
import random

# FULL SESSION DATA FROM YOUR BROWSER
PINTEREST_SESS = "TWc9PSY4Z2tSUUxObEZueXh2bDg1ZjdkU2NUY1g1VzI1dUl3T21sQzk2M1NJOFNTaTB3aWltQ2JUcDY5TlRaMmcrWi8zRm4ra3R5MVVFT0NiRGxpeGgyYld4UzkzUy9DYnA5TnJWM09zT29zVDNCRGJRRGhzM3pEeGdWMHNXZ2xvczB3ak9jMml1aWZad3BUd3A2b1dJazNnVDlPS2ZSeGZ5QkVnZVZWNStIUTJKeUJsRTQ2ZXZRSWZGU3J6YVlxeWxRefoSRGVnclFvMkxXNXc5YkdGaXQ1dnNFMFYxTW1HTTVtSDdrSTYzQmJhTVBGVTVxTG9CeDRWZUY2TTRaYzhGYmw1eXgwbzdFSzJ1WGFKVjRUYmh1bWRIT3RCSXJkakRhUk9MR09nT3RvNFNEK0twYVkycVlXbXRWRnJCZkNjR29rT3AxdE1FOFBLZUlLMmNlc1ltOHNlZUxEOEs5K05XdEtNY20wb1MyTHFOQmhsdkFaN2pyWm4vTElldHB2bzZka2xnTTBFVTFoL3U1enlHWis5N2tOYWxTRVZnOTJrZTUzK3ZidU4zdGsrY0ZocTByYnp3V21OTllXSGEyUzQzeU1BeW4rSWJ2Z3ZlMDRtZHhxQ0VPVnk1SEcraStNbFc2aS9NNGN6SmRlT1BqWU1RWW1XYVdydnlySkI0SVJGQ1lOckhwK0FOSFV6cnJLTzZCTEYzeVlQb3JpTGpvRHp2K1RmS3crS2JWd05HSjJEd2Z2a0MxUXRjOVArdmlqOWVXRmdaUW1qQUtVQzNSa1FmV2hVRW9NdU1OcFdCNDZnWmtDQ1hhMGZFZHJ5Y3BpTU9NaGpaeG9jS3ZLYXNuZTdUZmFpVWtzcHJlQkZ4L0VsSFMxR1VhNjFEVXdsUHBzR21QN2xpR1RiVEdOUTBDU2ZEa2ZKQ3UyV1dRdmxxMXAvNStiaWdRMG9MZ3k3NHJ5VGVkdFFNMEI1SndhWVdja3hnbkRrdyt2eVJEUmJybmE4cnk4YzNkb3l6YldBNDRNQnNhMnB1T2ZFVVlOd2RYVC9QR3lPb0tHVUNyakxUSDdqUXZRVlRJUE15VDFZMXFhYU1IV3k4L3p1b0R1MzhoRS9yV05xRUNYcGYrZ2UydDJjcGpFaEFIUXhJNG5VcVUrZGRoeUVMUy92V0ZlUDYrRERlWVorZVo3aUk4SUVleUFMdVVtOXAwMUh1SXplaFZsUFhSQmZkWHYzRVJXUGJHUGM1SWJBVVpESzlnUlJXT3NLV3FpdTU1aFptelRQNUJ1NDFpVnNMRkFjbDQwT1BHbzN3ZmdxcUZpTGFhbUwvYmx3QlY3VDEyMU83Z3k2RzljRTBFTU11L25TbmdXODg4KzlqZ2VVa3l2NEhvVWxwSlZ0SlduYVh5S3VFMVd6azNxeXpuQ2J0MVF5dGNOZ081K0RnaE1zUEQ1WGdMOXBqKzJ5bkMrMzB4eWxIa21leHpLd1J2Tlk3TzlPbmMrK2VCWDVDeXBtVURTdmZ3alVtN0NhWGZIdE1Tai9KUlRqYlMra2hJZ3hYZUdKN3VOMDFiVHpJeHZPeSswdTUyUi8wN25ZT3JUNkdsRyt2MmtNYVNRY085c2lLOHFFTk1IMDhSTVJxVWdIVmo0ZE9uRm8yVUFjejgwRjluTG1IUFh0U0JoKzlEY3B4MW1abnlDTytRckE5S1dYWmg5T0pxVnpPaWRtRm1UQVlYU3JKa04reHViWk5jY2JiMkZPMXZ0Y0ZvNCtBSTUrZVh4eHgxL0lISWJjTXlWSFJubXN4alI5UU94YTJ4UWkmeWVXNUUrUEJUdTdjblkvMGQ2b0V6Y0hPYkJzPQ=="
PINTEREST_B    = "AZIpHjrMDn1MOYcsNeQtSLrarNlSD8SIp0YrRFXePGfLn8WxPDqoEe8ZA++rcuMQcBQ="
CSRF_TOKEN     = "19ef0946f9d6847c3f4b3b9d6d9111cb"

def scrape_home_feed(limit=20):
    print(f"Scraping Pinterest Home Feed (ph.pinterest.com) limit: {limit}")
    candidates = []
    seen_images = set()
    bookmarks = [""]

    # Full cookies string
    cookie_str = f"_pinterest_sess={PINTEREST_SESS}; _b=\"{PINTEREST_B}\"; csrftoken={CSRF_TOKEN}; _auth=1"

    headers = {
        "User-Agent":              "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie":                  cookie_str,
        "X-Pinterest-AppState":    "active",
        "X-CSRFToken":             CSRF_TOKEN,
        "X-Requested-With":        "XMLHttpRequest",
        "Accept":                  "application/json, text/javascript, */*; q=0.01",
        "Referer":                 "https://ph.pinterest.com/",
    }

    while len(candidates) < limit:
        args = {
            "options": {"bookmarks": bookmarks, "field_set_key": "main_grid", "is_homefeed": True},
            "context": {},
        }
        # Using ph.pinterest.com as seen in user's screenshot
        url = (
            "https://ph.pinterest.com/resource/UserHomeFeedResource/get/"
            f"?data={urllib.parse.quote(json.dumps(args))}"
        )

        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"Error {response.status_code}: {response.text[:200]}")
                break

            resp_json = response.json()
            resource_response = resp_json.get("resource_response", {})
            data_list         = resource_response.get("data", [])

            if not data_list:
                print("No data in feed.")
                break

            for item in data_list:
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
            time.sleep(random.uniform(1.0, 2.0))
        except Exception as e:
            print(f"Scrape error: {e}")
            break

    return candidates[:limit]

def main():
    output_dir = "scraped_home_feed"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    urls = scrape_home_feed(limit=20)
    print(f"Found {len(urls)} images. Downloading...")

    for i, url in enumerate(urls):
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                filename = f"home_feed_{i}.jpg"
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                print(f"  Downloaded: {filename}")
        except: pass

if __name__ == "__main__":
    main()
