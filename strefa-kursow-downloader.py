import json
import os
import requests
from datetime import datetime
import sys
import argparse
from urllib.parse import urlparse
import getpass
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
        password = getpass.getpass("Enter your password: ")

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
        print(f"Błąd: Nie udało się pobrać tokena. {response.status_code} - {response.text}")
        sys.exit(1)

# Function to get the token from the file or prompt user
def retrieve_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as token_file:
            token_data = json.load(token_file)
            token = token_data["value"]
            valid_until = token_data["validUntil"]
            if not is_token_expired(token):
                return token
            else:
                print("Token stracił ważność. Loguję ponownie by pobrać aktualny...")
    return get_token()

# Function to get the list of courses
def get_courses(token):
    url = f"{API_BASE_URL}/web/course"
    headers = {"x-platforma-token": token}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Błąd: Nie udało się pobrać listy kursów. {response.status_code} - {response.text}")
        sys.exit(1)

# Function to get course details
def get_course_details(course_id, token):
    url = f"{API_BASE_URL}/web/course/{course_id}"
    headers = {"x-platforma-token": token}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Błąd: Nie udało się pobrać zawartości kursu. {response.status_code} - {response.text}")
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
        print(f"Błąd pobierania linków do filmów dla lekcji {resource_id}: {e}")
        return {}

# Function to sanitize filenames
def sanitize_filename(name):
    return "".join(c if c.isalnum() or c in ("_", "-", ".") else "_" for c in name)

# Function to download a file
def download_file(url, output_path, referer):
    print(f"Pobieram {output_path}")
    response = requests.get(url, headers={"Referer": referer}, stream=True)
    if response.status_code == 200:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file.write(chunk)
    else:
        print(f"Błąd: Nie udało się pobrać {url}. Kod odpowiedzi: {response.status_code}")

# Function to download course materials
def download_material(course_id, token, output_dir):
    material_url = f"{API_BASE_URL}/web/course/{course_id}/material"
    headers = {"x-platforma-token": token}
    response = requests.get(material_url, headers=headers)

    if response.status_code == 200:
        material_data = response.json()
        material_file_url = material_data.get("url")

        if material_file_url:
            file_name = os.path.basename(urlparse(material_file_url).path)
            output_path = os.path.join(output_dir, file_name)
            download_file(material_file_url, output_path, PLATFORM_REFERER)
        else:
            print("Brak materiałów dla kursu.")
    else:
        print(f"Błąd pobierania lekcji dla kursu {course_id}. {response.status_code} - {response.text}")
# Main function
def main():
    parser = argparse.ArgumentParser(description="Strefa Kursow Downloader")
    parser.add_argument("-t", "--token", help="Platform token")
    parser.add_argument("-c", "--courseurl", help="Course URL")
    parser.add_argument("-o", "--outputdir", default="downloads", help="Directory to save downloaded videos")
    parser.add_argument("--save-json", action="store_true", help="Save JSON responses to a debug log")
    parser.add_argument("--save-materials", action="store_true", help="Download course materials if available")
    parser.add_argument("--save-subtitles", action="store_true", help="Download subtitles if available")

    args = parser.parse_args()

    # Step 1: Retrieve or ask for token
    token = args.token or retrieve_token()

    # Step 2: If no course URL is provided, fetch all available courses
    if not args.courseurl:
        courses = get_courses(token)
        print("Dostępne kursy:")
        print("0: Pobierz wszystkie")
        for i, course in enumerate(courses, start=1):  # Start numbering from 1
            print(f"{i}: {course['name']} (ID: {course['id']})")

        course_choices = input("Wpisz numery kursów do pobrania (możesz pobrać kilka oddzielając numery przecinkami np. 1,3,4): ")
        course_choices = [choice.strip() for choice in course_choices.split(",")]

        if "0" in course_choices:
            course_ids = [course['id'] for course in courses]
        else:
            try:
                course_ids = [courses[int(choice) - 1]['id'] for choice in course_choices if choice.isdigit()]
            except (IndexError, ValueError):
                print("Wybrałeś zły numer.")
                sys.exit(1)
    else:
        # Step 3: Retrieve course ID from URL
        course_id = int(args.courseurl.split("/")[-1])
        course_ids = [course_id]

    # Step 4: Download the selected courses
    for course_id in course_ids:
        course_details = get_course_details(course_id, token)
        course_name = sanitize_filename(course_details.get("name", "Unknown_Course")).replace(" ", "_")
        chapters = course_details.get("chapters", [])
        course_output_dir = os.path.join(args.outputdir, course_name)

        print(f"\Kurs: {course_name}")
        print(f"Znaleziono {len(chapters)} rozdziałów.")
        
        # Step 5: Download course materials if requested
        if args.save_materials:
            download_material(course_id, token, course_output_dir)
        
        # Step 6: Iterate through chapters and resources
        for chapter_index, chapter in enumerate(chapters, start=1):
            chapter_title = sanitize_filename(chapter.get("title", "Unknown_Chapter")).replace(" ", "_")
            chapter_name = f"{chapter_index:02d}_{chapter_title}"
            resources = chapter.get("resources", [])
            print(f"Ilość lekcji rozdziału: {chapter_name} ({len(resources)})")

            for resource_index, resource in enumerate(resources, start=1):
                resource_name = sanitize_filename(resource.get("name", "Unknown_Resource")).replace(" ", "_")
                resource_id = resource["id"]
                resource_type = resource.get("type", "unknown")

                # Skip non-video resources
                if resource_type != "video":
                    print(f"Pomijam element nie zawierający video: {resource_name} (type: {resource_type})")
                    continue

                # Get signed URL
                signed_url_data = get_signed_url(resource_id, token)
                video_url = signed_url_data.get("url")

                if video_url:
                    # Determine output file path
                    parsed_url = urlparse(video_url)
                    file_name = os.path.basename(parsed_url.path)
                    reversed_file_name = f"{chapter_name}_{resource_index:02d}_{resource_name}{os.path.splitext(file_name)[1]}"
                    output_path = os.path.join(course_output_dir, reversed_file_name)

                    # Download the video
                    download_file(video_url, output_path, PLATFORM_REFERER)
                else:
                    print(f"Lekcja {resource_name} nie ma video.")
                
                # Download subtitles if requested
                if args.save_subtitles:
                    for lang_key, subtitle_url in signed_url_data.items():
                        if lang_key.startswith("subtitle") and subtitle_url:
                            lang_suffix = ""
                            if lang_key != "subtitleUrl":  # Default subtitle has no suffix
                                lang_suffix = f"-{lang_key.replace('subtitle', '').replace('Url', '').upper()}"
                            subtitle_file_name = f"{chapter_name}_{resource_index:02d}_{resource_name}{lang_suffix}.vtt"
                            subtitle_output_path = os.path.join(course_output_dir, subtitle_file_name)
                            download_file(subtitle_url, subtitle_output_path, PLATFORM_REFERER)


# Start the program
if __name__ == "__main__":
    main()
