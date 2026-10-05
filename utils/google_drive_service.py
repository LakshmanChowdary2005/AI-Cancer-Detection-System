import os
import json

def upload_to_google_drive(file_path, folder_name="MediScan_AI_Reports"):
    """
    Uploads a file to Google Drive via Google Drive API v3.
    If credentials are missing or unconfigured, falls back to local storage and returns status info.
    """
    if not os.path.exists(file_path):
        return {"success": False, "error": "File does not exist.", "status": "Failed"}

    file_name = os.path.basename(file_path)

    # Check for service account json file or env vars
    sa_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "service_account.json")
    
    if not os.path.exists(sa_path) and not os.environ.get("GDRIVE_CLIENT_ID"):
        print(f"Google Drive API: Service account or OAuth credentials not detected at '{sa_path}'. File saved locally at {file_path}")
        return {
            "success": True,
            "drive_status": "Saved Locally (Pending Google Drive API Credentials)",
            "file_name": file_name,
            "local_path": file_path,
            "drive_url": None,
            "file_id": None
        }

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        SCOPES = ['https://www.googleapis.com/auth/drive.file']
        creds = service_account.Credentials.from_service_account_file(sa_path, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)

        # 1. Search or create target folder
        query = f"name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = service.files().list(q=query, fields="files(id, name)").execute()
        folders = results.get('files', [])

        if not folders:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
        else:
            folder_id = folders[0].get('id')

        # 2. Upload file to folder
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        media = MediaFileUpload(file_path, mimetype='application/pdf')
        drive_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()

        file_id = drive_file.get('id')
        web_link = drive_file.get('webViewLink')

        print(f"Successfully uploaded {file_name} to Google Drive: {web_link}")
        return {
            "success": True,
            "drive_status": "Uploaded to Google Drive",
            "file_name": file_name,
            "local_path": file_path,
            "drive_url": web_link,
            "file_id": file_id
        }

    except Exception as e:
        print(f"Google Drive Upload Error: {e}")
        return {
            "success": True, # Keep success true as file is safe locally
            "drive_status": f"Saved Locally ({str(e)})",
            "file_name": file_name,
            "local_path": file_path,
            "drive_url": None,
            "file_id": None
        }
