import os
import mimetypes
import time
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import googleapiclient.discovery
import googleapiclient.errors
import googleapiclient.http

SCOPES = ['https://www.googleapis.com/auth/drive']
# Create main window
root = tk.Tk()
root.title("Automatic Backup")

# Create and place the interface elements
# Directory selection
dir_label = tk.Label(root, text="Select Directories to Backup:")
dir_label.pack()
dir_listbox = tk.Listbox(root, selectmode=tk.MULTIPLE, width=50, height=10)
dir_listbox.pack()
add_dir_button = tk.Button(root, text="Add Directory", command=lambda: dir_listbox.insert(tk.END, filedialog.askdirectory()))
add_dir_button.pack()
remove_dir_button = tk.Button(root, text="Remove Selected", command=lambda: dir_listbox.delete(tk.ACTIVE))
remove_dir_button.pack()

# Backup location
folder_id_label = tk.Label(root, text="Enter Google Drive Folder ID:")
folder_id_label.pack()
folder_id_entry = tk.Entry(root, width=50)
folder_id_entry.pack()

# Backup frequency
frequency_label = tk.Label(root, text="Select Backup Frequency (in minutes):")
frequency_label.pack()
frequency_spinbox = tk.Spinbox(root, from_=1, to=999, width=5)
frequency_spinbox.pack()

def start_backup():
    directories = dir_listbox.get(0, tk.END)
    folder_id = folder_id_entry.get()  
    frequency = int(frequency_spinbox.get())
    
    # Validate the inputs
    if not directories:
        messagebox.showerror("Error", "Please select at least one directory to backup.")
        return
    if not folder_id:
        messagebox.showerror("Error", "Please enter a Google Drive Folder ID.")
        return
    
    # Set the maximum value of the progress bar
    total_files = 0
    for directory in directories:
        for foldername, subfolders, filenames in os.walk(directory):
            total_files += len(filenames)
    progress_bar['maximum'] = total_files
    
    # Start the backup thread
    backup_thread = threading.Thread(target=backup, args=(directories, folder_id, frequency))
    backup_thread.start()

# Start backup button
start_button = tk.Button(root, text="Start Backup", command=start_backup)
start_button.pack()

# Progress bar
progress_bar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progress_bar.pack()

# Status label
status_label = tk.Label(root, text="Status: Ready")
status_label.pack()

# Implement the backup logic


def backup_to_drive(drive_service, local_path, parent_folder_id=None):
    """Backup a local path (file or directory) to Google Drive."""
    
    if os.path.isfile(local_path):
        # If it's a file, upload it.
        upload_file_to_drive(drive_service, local_path, parent_folder_id)
    
    elif os.path.isdir(local_path):
        folder_name = os.path.basename(local_path)
        
        # Check if this folder exists on Google Drive.
        folder_id = get_folder_id(drive_service, folder_name, parent_folder_id)
        
        # If not, create it.
        if folder_id is None:
            folder_id = create_folder(drive_service, folder_name, parent_folder_id)
        
        # Recursively backup all items in this directory.
        for item_name in os.listdir(local_path):
            backup_to_drive(drive_service, os.path.join(local_path, item_name), folder_id)

def get_file_id(drive_service, file_name, parent_id=None):
    """Get the file ID or None if not found."""
    query = f"name='{file_name}'"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    response = drive_service.files().list(q=query, spaces='drive').execute()
    for file in response.get('files', []):
        if file['name'] == file_name:
            return file['id']
    return None

def get_folder_id(drive_service, folder_name, parent_id=None):
    """Get the folder ID or None if not found."""
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
    if parent_id:
        query += f" and '{parent_id}' in parents"
    response = drive_service.files().list(q=query, spaces='drive').execute()
    for file in response.get('files', []):
        if file['name'] == folder_name:
            return file['id']
    return None

def create_folder(drive_service, folder_name, parent_id=None):
    """Create a folder and return its ID."""
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        folder_metadata['parents'] = [parent_id]
    folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
    return folder['id']

def upload_file_to_drive(drive_service, local_path, parent_id=None):
    """Upload a file to Google Drive. If a file with the same name exists in the destination, remove it."""
    file_name = os.path.basename(local_path)
    
    # Check for existing files with the same name in the destination folder.
    existing_file_id = get_file_id(drive_service, file_name, parent_id)
    if existing_file_id:
        # Delete the existing file.
        drive_service.files().delete(fileId=existing_file_id).execute()

    file_metadata = {'name': file_name}
    if parent_id:
        file_metadata['parents'] = [parent_id]
    
    media = MediaFileUpload(local_path, mimetype=mimetypes.guess_type(local_path)[0])
    drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

def backup(directories, folder_id, frequency):
    """
    Backs up the specified directories to the Google Drive folder with the given folder_id.
    """
    # Load credentials and set up the Drive API client
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json')
    
    service = build('drive', 'v3', credentials=creds)

    while True:
        for directory in directories:
            try:
                backup_to_drive(service, directory, folder_id)
                print(f"Backed up: {directory} to Drive folder: {folder_id}")
            except Exception as e:
                print(f"Error backing up {directory}: {e}")
        
        time.sleep(frequency * 60)  # Convert frequency to seconds and sleep

# Run the main loop
root.mainloop()
