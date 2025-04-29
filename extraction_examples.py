"""
Crawl4AI to Google Docs Integration (Aggregate Multiple URLs to Single Updated Doc) - FINAL
This script:
1. Defines a list of URLs to crawl (A-Z Guide + 3 others).
2. Authenticates with Google Drive API once.
3. Creates/finds a target folder in Google Drive once.
4. Crawls all URLs and aggregates the markdown content into a single string.
5. Finds the specific target Google Doc (e.g., "Rays Combined Website Content") by name.
6. Deletes the existing target Google Doc if found.
7. Uploads the FULL aggregated content as markdown, converts it to a
   new Google Doc with the target name, and cleans up the markdown upload.
8. Provides a summary.
"""

import asyncio
import os
import pickle
import re # Keep for potential sanitization if needed later
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

# Import Crawl4AI components
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

# Import Google Drive API components
try:
    from googleapiclient.discovery import build, Resource
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
except ImportError:
    print("Required Google libraries not found. Please install them:")
    print("pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")
    exit()

# --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_PICKLE_FILE = 'token.pickle'
OUTPUT_DIR = "rays_aggregate_temp" # Temp dir for local markdown before upload
# Define the single target Google Doc name for ALL aggregated content
TARGET_COMBINED_DOC_NAME = "Rays Combined Website Content"
# --- End Configuration ---


# --- Crawl4AI Functions ---
async def crawl_and_get_content(url: str) -> Optional[str]:
    """Crawl a URL and return the full markdown content as a string."""
    # (This function remains the same - gets full content for one URL)
    print(f"\n--- Starting Crawl for: {url} ---")
    content = None
    try:
        browser_config = BrowserConfig(headless=True)
        markdown_generator = DefaultMarkdownGenerator(content_filter=PruningContentFilter())
        crawler_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            markdown_generator=markdown_generator
        )
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=url, config=crawler_config)
            if not result or not result.success:
                print(f"!!! Crawling failed for {url}. Error: {result.error_message if result else 'Unknown error'}")
                return None
            print("Crawling successful.")
            content = getattr(result.markdown, 'fit_markdown', result.markdown)
            if not content or len(content.strip()) == 0 :
                 print(f"!!! Warning: Crawled content for {url} is empty after filtering.")
                 return None
    except Exception as e:
        print(f"!!! An error occurred during crawling for {url}. Error: {str(e)}")
        return None
    print(f"--- Crawl Complete for: {url} ---")
    return content

# --- Google Drive Functions ---

def authenticate_google_drive() -> Optional[Resource]:
    """Authenticate with Google Drive API using OAuth2"""
    # (This function remains the same)
    print("\n--- Authenticating with Google Drive ---")
    creds = None
    if os.path.exists(TOKEN_PICKLE_FILE):
        try:
            with open(TOKEN_PICKLE_FILE, 'rb') as token:
                creds = pickle.load(token)
            print("Loaded credentials from token.pickle.")
        except Exception as e:
            print(f"!!! Could not load token.pickle: {e}. Re-authentication required.")
            creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Refreshing expired credentials...")
                creds.refresh(Request())
                print("Credentials refreshed successfully.")
            except Exception as e:
                print(f"!!! Could not refresh token: {e}. Re-authentication required.")
                creds = None
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"!!! ERROR: Cannot find {CREDENTIALS_FILE}.")
                return None
            try:
                print("No valid credentials found or refresh failed. Starting authentication flow...")
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0, prompt='consent', authorization_prompt_message='Please authorize access to Google Drive:\n{url}')
                print("Authentication successful.")
            except Exception as e:
                print(f"!!! Authentication flow failed: {str(e)}")
                return None
        try:
            with open(TOKEN_PICKLE_FILE, 'wb') as token:
                pickle.dump(creds, token)
            print(f"Credentials saved to {TOKEN_PICKLE_FILE}.")
        except Exception as e:
             print(f"!!! Warning: Could not save credentials to {TOKEN_PICKLE_FILE}: {e}")
    try:
        service = build('drive', 'v3', credentials=creds)
        print("Google Drive service built successfully.")
        print("--- Authentication Complete ---")
        return service
    except Exception as e:
        print(f"!!! Failed to build Google Drive service: {str(e)}")
        print("--- Authentication Failed ---")
        return None

def create_folder(service: Resource, folder_name: str, parent_folder_id: Optional[str] = None) -> Optional[str]:
    """Create a folder in Google Drive if it doesn't exist, return its ID"""
    # (This function remains the same)
    print(f"\n--- Checking/Creating Google Drive Folder: '{folder_name}' ---")
    try:
        query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
        if parent_folder_id:
            query += f" and '{parent_folder_id}' in parents"
        else:
             query += " and 'root' in parents"
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        folders = response.get('files', [])
        if folders:
            folder_id = folders[0].get('id')
            print(f"Folder '{folder_name}' already exists with ID: {folder_id}")
            return folder_id
        else:
            print(f"Folder '{folder_name}' not found. Creating...")
            folder_metadata = {'name': folder_name, 'mimeType': 'application/vnd.google-apps.folder'}
            if parent_folder_id:
                folder_metadata['parents'] = [parent_folder_id]
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
            print(f"Folder '{folder_name}' created successfully with ID: {folder_id}")
            return folder_id
    except HttpError as error:
        print(f"!!! An error occurred creating/checking folder: {error}")
        return None
    except Exception as e:
        print(f"!!! An unexpected error occurred during folder creation/check: {str(e)}")
        return None

def find_google_doc_id(service: Resource, doc_name: str, folder_id: str) -> Optional[str]:
    """Finds a Google Doc by exact name within a specific folder"""
    # (This function remains the same)
    print(f"\n--- Searching for existing Google Doc: '{doc_name}' in folder {folder_id} ---")
    try:
        escaped_doc_name = doc_name.replace("'", "\\'")
        query = (
            f"name='{escaped_doc_name}' and "
            f"mimeType='application/vnd.google-apps.document' and "
            f"'{folder_id}' in parents and "
            f"trashed=false"
        )
        response = service.files().list(q=query, spaces='drive', fields='files(id, name)', pageSize=1).execute()
        files = response.get('files', [])
        if files:
            doc_id = files[0].get('id')
            print(f"Found existing Google Doc with ID: {doc_id}")
            return doc_id
        else:
            print("Existing Google Doc not found.")
            return None
    except HttpError as error:
        print(f"!!! An error occurred searching for the Google Doc: {error}")
        return None
    except Exception as e:
        print(f"!!! An unexpected error occurred during Doc search: {str(e)}")
        return None

def delete_google_drive_file(service: Resource, file_id: str):
    """Deletes a file from Google Drive by its ID"""
    # (This function remains the same)
    print(f"\n--- Deleting Google Drive File ID: {file_id} ---")
    try:
        service.files().delete(fileId=file_id).execute()
        print("File deleted successfully.")
    except HttpError as error:
        if error.resp.status == 404:
             print("File not found (already deleted?). Continuing...")
        else:
             print(f"!!! An error occurred deleting the file: {error}")
    except Exception as e:
        print(f"!!! An unexpected error occurred during file deletion: {str(e)}")

def upload_and_convert_markdown(service: Resource, full_markdown_content: str, target_doc_name: str, folder_id: str) -> Optional[Tuple[str, str]]:
    """
    Saves the FULL markdown locally, uploads it to Drive, converts it to a Google Doc
    with the target name, and cleans up the uploaded markdown.
    """
    # (This function remains the same - handles the full content)
    print(f"\n--- Uploading and Converting Full Content to Google Doc: '{target_doc_name}' ---")
    local_temp_filepath = None
    uploaded_md_id = None
    new_doc_id = None
    new_doc_link = None
    try:
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
        # Use a consistent temp name for the full aggregated content
        safe_temp_name = re.sub(r'[\\/*?:"<>|]', '-', target_doc_name) # Sanitize base name
        local_temp_filepath = os.path.join(OUTPUT_DIR, f"temp_{safe_temp_name}_aggregated.md")
        with open(local_temp_filepath, "w", encoding="utf-8") as f:
            f.write(full_markdown_content)
        print(f"Saved aggregated content locally to: {local_temp_filepath}")
        md_filename_on_drive = f"{target_doc_name}_Source.md"
        md_metadata = {'name': md_filename_on_drive, 'parents': [folder_id]}
        media = MediaFileUpload(local_temp_filepath, mimetype='text/markdown', resumable=True)
        print(f"Uploading temporary markdown '{md_filename_on_drive}'...")
        uploaded_md_file = service.files().create(body=md_metadata, media_body=media, fields='id').execute()
        uploaded_md_id = uploaded_md_file.get('id')
        if not uploaded_md_id:
            raise Exception("Failed to get ID for uploaded markdown file.")
        print(f"Temporary markdown uploaded successfully with ID: {uploaded_md_id}")
        docs_metadata = {
            'name': target_doc_name,
            'mimeType': 'application/vnd.google-apps.document',
            'parents': [folder_id]
        }
        print(f"Converting uploaded markdown to Google Doc named '{target_doc_name}'...")
        docs_file = service.files().copy(fileId=uploaded_md_id, body=docs_metadata, fields='id, name, webViewLink').execute()
        new_doc_id = docs_file.get('id')
        new_doc_link = docs_file.get('webViewLink')
        print(f"Successfully created Google Doc: '{docs_file.get('name')}'")
        print(f"New Google Doc ID: {new_doc_id}")
        print(f"View Link: {new_doc_link}")
    except HttpError as error:
        print(f"!!! An error occurred during upload/conversion for '{target_doc_name}': {error}")
        return None
    except Exception as e:
        print(f"!!! An unexpected error occurred during upload/conversion for '{target_doc_name}': {str(e)}")
        return None
    finally:
        if uploaded_md_id:
            try:
                print(f"\n--- Deleting Temporary Uploaded Markdown File ID: {uploaded_md_id} ---")
                service.files().delete(fileId=uploaded_md_id).execute()
                print("Temporary markdown file deleted successfully from Drive.")
            except Exception as del_e:
                 print(f"!!! Warning: Failed to delete temp markdown file {uploaded_md_id}: {del_e}")
        if local_temp_filepath and os.path.exists(local_temp_filepath):
            try:
                os.remove(local_temp_filepath)
                print(f"Deleted temporary local file: {local_temp_filepath}")
            except Exception as e:
                print(f"!!! Warning: Failed to delete local temp file {local_temp_filepath}: {e}")
    if new_doc_id and new_doc_link:
        return new_doc_id, new_doc_link
    else:
        return None


# --- Main Execution Logic ---
async def main():
    """Main function to crawl multiple URLs and update ONE single Google Doc with aggregated content."""
    print("======= Starting Rays Multi-URL Crawler & Single Doc Updater =======") # <-- Updated title

    # --- Define List of URLs to Crawl ---
    urls_to_crawl = [
        "https://www.mlb.com/rays/ballpark/gms-field/a-z-guide",
        "https://www.mlb.com/rays/tickets/specials/rays-rush",
        "https://www.mlb.com/rays/tickets/specials/salute-to-service",
        "https://www.mlb.com/rays/tickets/specials/student-ticket-offers",
        "https://www.mlb.com/rays/tickets/season-tickets/season-membership",
        "https://www.mlb.com/rays/tickets/single-game-tickets",
        "https://www.mlb.com/rays/tickets/premium/suites",
        "https://www.mlb.com/rays/gaming" 

    ]
    print(f"Target URLs: {urls_to_crawl}")

    # --- Single Authentication and Folder Setup ---
    drive_service = authenticate_google_drive()
    if not drive_service:
        print("\n!!! Google Drive authentication failed. Exiting.")
        print("======= Script Finished (with auth errors) =======")
        return

    # Define folder name (daily or fixed)
    folder_name = f"Rays Combined Content - {datetime.now().strftime('%Y-%m-%d')}"
    target_folder_id = create_folder(drive_service, folder_name)
    if not target_folder_id:
        print("\n!!! Failed to create or find Google Drive folder. Cannot proceed.")
        print("======= Script Finished (with folder errors) =======")
        return
    print(f"--- Using Google Drive Folder: '{folder_name}' (ID: {target_folder_id}) ---")

    # --- Crawl URLs and Aggregate Content ---
    aggregated_markdown = "" # Initialize empty string for aggregation
    crawl_statuses: List[Dict] = []

    print("\n======= Starting URL Crawling & Aggregation Phase =======") # <-- Updated phase name
    for url in urls_to_crawl:
        content = await crawl_and_get_content(url)
        if content:
            # Add a separator and the source URL to the aggregated content
            aggregated_markdown += f"\n\n{'='*40}\n## Content from: {url}\n{'='*40}\n\n{content}"
            crawl_statuses.append({"url": url, "status": "Success"})
        else:
            crawl_statuses.append({"url": url, "status": "Failed or Empty"})

    # --- Check if any content was aggregated ---
    if not aggregated_markdown.strip():
        print("\n!!! No content successfully crawled from any URL. Nothing to update. Exiting.")
        print("======= Script Finished (no content) =======")
        return

    # --- Process the Aggregated Content into One Doc ---
    print("\n======= Starting Single Google Doc Update Phase =======")

    # --- Find and Delete Existing Target Google Doc ---
    # Use the single TARGET_COMBINED_DOC_NAME defined in configuration
    existing_doc_id = find_google_doc_id(drive_service, TARGET_COMBINED_DOC_NAME, target_folder_id)
    if existing_doc_id:
        delete_google_drive_file(drive_service, existing_doc_id)
    else:
        print(f"No existing doc named '{TARGET_COMBINED_DOC_NAME}' found to delete. Will create anew.")

    # --- Upload Aggregated Content and Convert to the Target Google Doc ---
    update_result = upload_and_convert_markdown(
        drive_service,
        aggregated_markdown,       # Pass the full aggregated markdown
        TARGET_COMBINED_DOC_NAME,  # Use the single target name
        target_folder_id
    )

    # --- Final Summary ---
    print("\n======= Script Execution Summary =======")
    print(f"Processed {len(urls_to_crawl)} URLs.")
    print(f"Target Combined Google Doc: '{TARGET_COMBINED_DOC_NAME}'")
    print(f"Target Drive Folder: '{folder_name}' (ID: {target_folder_id})")

    print("\n--- Crawl Statuses: ---")
    for status in crawl_statuses:
        print(f"  - URL: {status['url']} -> Status: {status['status']}")

    if update_result:
        new_doc_id, new_doc_link = update_result
        print("\n--- Google Doc Update Status: ---")
        print(f"  Status: Success")
        print(f"  Document ID: {new_doc_id}") # The ID of the newly created/replaced doc
        print(f"  View Updated Doc: {new_doc_link}")
    else:
        print("\n--- Google Doc Update Status: ---")
        print(f"  Status: Failed")
        print(f"  Attempted Title: '{TARGET_COMBINED_DOC_NAME}'")
        print("  The Google Doc may not have been created or updated correctly.")

    print("\n======= Script Finished =======")


if __name__ == "__main__":
    import re # Keep re import
    # (Optional Playwright check)
    try:
        import playwright
    except ImportError:
         print("Playwright not found...")
         # exit()

    # Run the main async function
    asyncio.run(main())
