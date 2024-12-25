import os
import requests
from urllib.parse import urlparse
import argparse
import re
import json
from datetime import datetime

# Base URLs
API_BASE = "https://api.strefakursow.pl/api/v2/web"
LOGIN_URL = "https://api.strefakursow.pl/api/v2/sso/login"
PLATFORM_REFERER = "https://platforma.strefakursow.pl"

# Headers template
HEADERS_TEMPLATE = {
    "x-platforma-token": "",  # Token to be populated by user
    "Referer": PLATFORM_REFERER
}

def sanitize_filename(filename):
    """Sanitize filename to remove invalid characters."""
    return re.sub(r'[<>:"/\\|?*]', '_', filename)

def log_debug_data(url, json_data, debug_file):
    """Log the URL and JSON response to a debug file."""
    if debug_file:
        with open(debug_file, "a", encoding="utf-8") as f:
            f.write(f"URL: {url}\n")
            f.write(f"JSON Data: {json.dumps(json_data, ensure_ascii=False, indent=4)}\n")
            f.write("-" * 50 + "\n")

def get_course_details(course_id, token, debug_file=None):
    """Fetch course details."""
    url = f"{API_BASE}/course/{course_id}"
    headers = HEADERS_TEMPLATE.copy()
    headers["x-platforma-token"] = token
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    json_data = response.json()
    log_debug_data(url, json_data, debug_file)
    return json_data

def get_signed_url(resource_id, token, debug_file=None):
    """Fetch signed URL for a resource."""
    url = f"{API_BASE}/resource/{resource_id}/signed-url"
    headers = HEADERS_TEMPLATE.copy()
    headers["x-platforma-token"] = token
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    json_data = response.json()
    log_debug_data(url, json_data, debug_file)
    return json_data

def download_file(url, output_path, referer):
    """Download a file from a given URL."""
    headers = {"Referer": referer}
    response = requests.get(url, headers=headers, stream=True)
    response.raise_for_status()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    print(f"Downloaded: {output_path}")

def fetch_token():
    """Prompt for username/password and fetch the token."""
    username = input("Enter your email: ").strip()
    password = input("Enter your password: ").strip()
    
    payload = {
        "username": username,
        "password": password
    }
    
    response = requests.post(LOGIN_URL, json=payload)
    response.raise_for_status()
    token_data = response.json()
    return token_data

def load_or_fetch_token():
    """Load the token from file or fetch it if necessary."""
    token_file = "token.json"
    if os.path.exists(token_file):
        with open(token_file, "r", encoding="utf-8") as f:
            token_data = json.load(f)
        
        valid_until = datetime.fromisoformat(token_data["validUntil"])
        if datetime.now() < valid_until:
            print("Using saved token.")
            return token_data["value"]
        else:
            print("Saved token has expired.")
    
    # Fetch a new token if no valid token is found
    token_data = fetch_token()
    with open(token_file, "w", encoding="utf-8") as f:
        json.dump(token_data, f, ensure_ascii=False, indent=4)
    return token_data["value"]

def main(course_url, token=None, output_dir="downloads", debug_file=None):
    # Load or fetch token
    if not token:
        token = load_or_fetch_token()
    
    # Extract course ID from URL
    course_id = course_url.rstrip("/").split("/")[-1]
    
    # Step 1: Get course details
    course_details = get_course_details(course_id, token, debug_file)
    course_name = sanitize_filename(course_details.get("name", "Unknown_Course")).replace(" ", "_")
    chapters = course_details.get("chapters", [])
    
    print(f"Course: {course_name}")
    print(f"Found {len(chapters)} chapters.")
    
    # Step 2: Iterate through chapters and resources
    for chapter_index, chapter in enumerate(chapters, start=1):
        chapter_title = sanitize_filename(chapter.get("title", "Unknown_Chapter")).replace(" ", "_")
        chapter_name = f"{chapter_index:02d}_{chapter_title}"
        resources = chapter.get("resources", [])
        print(f"Chapter: {chapter_name} ({len(resources)} resources)")
        
        for resource_index, resource in enumerate(resources, start=1):
            resource_name = sanitize_filename(resource.get("name", "Unknown_Resource")).replace(" ", "_")
            resource_id = resource["id"]
            resource_type = resource.get("type", "unknown")

            # Skip non-video resources
            if resource_type != "video":
                print(f"Skipping non-video resource: {resource_name} (type: {resource_type})")
                continue
            
            # Get signed URL
            signed_url_data = get_signed_url(resource_id, token, debug_file)
            video_url = signed_url_data.get("url")
            
            if video_url:
                # Determine output file path
                parsed_url = urlparse(video_url)
                file_name = os.path.basename(parsed_url.path)
                reversed_file_name = f"{chapter_name}_{resource_index:02d}_{resource_name}{os.path.splitext(file_name)[1]}"
                output_path = os.path.join(output_dir, course_name, chapter_name, reversed_file_name)
                
                # Download the video
                download_file(video_url, output_path, PLATFORM_REFERER)
            else:
                print(f"Resource {resource_name} has no video URL.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Downloader for Strefa Kursów.")
    parser.add_argument("-c", "--courseurl", required=True, help="Course URL")
    parser.add_argument("-t", "--token", help="Platform token (optional)")
    parser.add_argument("-o", "--outputdir", default="downloads", help="Output directory for downloads")
    parser.add_argument("--save-json", action="store_true", help="Save JSON responses to debug log")
    
    args = parser.parse_args()
    debug_log_file = "debug_log.txt" if args.save_json else None
    main(args.courseurl, args.token, args.outputdir, debug_log_file)
