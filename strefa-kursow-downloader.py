import json
import os
import requests
from datetime import datetime
import sys
import argparse
from urllib.parse import urlparse

# Define some constants for headers and URLs
API_BASE_URL = "https://api.strefakursow.pl/api/v2"
PLATFORM_REFERER = "https://platforma.strefakursow.pl"
TOKEN_FILE = "token.json"

# Function to check if the token is expired
def is_token_expired(token):
    user_url = f"{API_BASE_URL}/web/user/me"
    headers = {"x-platforma-token": token}

    # Make the request to get the signed URL
    response = requests.get(user_url, headers=headers)
    if response.status_code == 200:
        return False
    else:
        return True

# Function to retrieve the token (or ask for credentials)
def get_token(username=None, password=None):
    if username is None or password is None:
        username = input("Enter your username (email): ")
        password = input("Enter your password: ")

    login_url = f"{API_BASE_URL}/sso/login"
    response = requests.post(login_url, json={"username": username, "password": password})

    if response.status_code == 200:
        data = response.json()
        token = data["value"]
        valid_until = data["validUntil"]

        # Save the token to a file
        with open(TOKEN_FILE, "w") as token_file:
            json.dump({"value": token, "validUntil": valid_until}, token_file)

        return token
    else:
        print(f"Error: Unable to retrieve token. {response.status_code} - {response.text}")
        sys.exit(1)

# Function to get the token from the file or prompt user
def retrieve_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as token_file:
            token_data = json.load(token_file)
            token = token_data["value"]
            valid_until = token_data["validUntil"]
            if not is_token_expired(token):
                print("not expired")
                return token
            else:
                print("Token expired. Re-authenticating...")
    return get_token()

# Function to get the list of courses
def get_courses(token):
    url = f"{API_BASE_URL}/web/course"
    headers = {"x-platforma-token": token}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: Unable to fetch courses. {response.status_code} - {response.text}")
        sys.exit(1)

# Function to get course details
def get_course_details(course_id, token):
    url = f"{API_BASE_URL}/web/course/{course_id}"
    headers = {"x-platforma-token": token}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: Unable to fetch course details. {response.status_code} - {response.text}")
        sys.exit(1)

def get_signed_url(resource_id, token, debug_file=None):
    # Define the API endpoint to fetch the signed URL
    signed_url_api = f"https://api.strefakursow.pl/api/v2/web/resource/{resource_id}/signed-url"
    
    headers = {
        "x-platforma-token": token,
    }

    try:
        # Make the request to get the signed URL
        response = requests.get(signed_url_api, headers=headers)
        response.raise_for_status()  # Raise an exception for 4xx/5xx responses

        # If the request is successful, parse the JSON response
        signed_url_data = response.json()

        # Optionally save the debug information
        if debug_file:
            debug_file.write(f"URL for resource {resource_id}: {signed_url_data}\n")

        return signed_url_data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching signed URL for resource {resource_id}: {e}")
        return {}

# Function to sanitize filenames
def sanitize_filename(name):
    return "".join(c if c.isalnum() or c in ("_", "-", ".") else "_" for c in name)

# Function to download a file
def download_file(url, output_path, referer):
    print(f"Downloading {output_path}")
    response = requests.get(url, headers={"Referer": referer}, stream=True)
    if response.status_code == 200:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file.write(chunk)
    else:
        print(f"Error: Failed to download {url}. Status code: {response.status_code}")

# Main function
def main():
    parser = argparse.ArgumentParser(description="Strefa Kursow Downloader")
    parser.add_argument("-t", "--token", help="Platform token")
    parser.add_argument("-c", "--courseurl", help="Course URL")
    parser.add_argument("-o", "--outputdir", default="downloads", help="Directory to save downloaded videos")
    parser.add_argument("--save-json", action="store_true", help="Save JSON responses to a debug log")

    args = parser.parse_args()

    # Step 1: Retrieve or ask for token
    token = args.token or retrieve_token()

    # Step 2: If no course URL is provided, fetch all available courses
    if not args.courseurl:
        courses = get_courses(token)
        print("Available courses:")
        print("0: Download all courses")
        for i, course in enumerate(courses, start=1):  # Start numbering from 1
            print(f"{i}: {course['name']} (ID: {course['id']})")

        course_choice = int(input("Enter the number of the course to download (0 for all): "))
        if course_choice == 0:
            course_ids = [course['id'] for course in courses]
        else:
            course_ids = [courses[course_choice - 1]['id']]  # Correcting index to 0-based

    else:
        # Step 3: Retrieve course ID from URL
        course_id = int(args.courseurl.split("/")[-1])
        course_ids = [course_id]

    # Step 4: Download the selected courses
    for course_id in course_ids:
        course_details = get_course_details(course_id, token)
        course_name = sanitize_filename(course_details.get("name", "Unknown_Course")).replace(" ", "_")
        chapters = course_details.get("chapters", [])

        print(f"\nCourse: {course_name}")
        print(f"Found {len(chapters)} chapters.")

        # Step 5: Iterate through chapters and resources
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
                signed_url_data = get_signed_url(resource_id, token)
                video_url = signed_url_data.get("url")

                if video_url:
                    # Determine output file path
                    parsed_url = urlparse(video_url)
                    file_name = os.path.basename(parsed_url.path)
                    reversed_file_name = f"{chapter_name}_{resource_index:02d}_{resource_name}{os.path.splitext(file_name)[1]}"
                    output_path = os.path.join(args.outputdir, course_name, chapter_name, reversed_file_name)

                    # Download the video
                    download_file(video_url, output_path, PLATFORM_REFERER)
                else:
                    print(f"Resource {resource_name} has no video URL.")

# Start the program
if __name__ == "__main__":
    main()
