# Dropbox Clone


### Functionality

- User Management: 
  - Add, Update and Delete users -> Administrator privileges.
  - User sessions - Login/Logout.
  - On user creation, generate root directory '/' specific to that user.
  
- File System Management: 
  - Upload Files: Upload file to GCP storage and create appropriate Firestore DB document to record the file/folder.
  - Rename: Check for duplicate names.
  - Move: Move files between folders.
  - Delete: Delete files. Check for files and sub-folders when deleting folders.
  - Navigation: User can navigate up and down the sub-directories.
  - Usage: Display number of files, folders, and total storage used by a user.

### Platforms

- Google Cloud Platform (GCP)
- NoSql Database - Google Firestore Database
- Storage - Google Cloud Storage
- Frontend - Bootstrap
- Backend - Python Flask Framework

### Initialization
1. Change the Project ID in config.py file.
2. Change the Google Cloud Storage Bucket ID in config.py file.

### Python Dependencies 

*use 'pip' to install these packages:*
1. flask
2. google.cloud.storage
3. firebase_admin
4. werkzeug
5. tempfile


### Running the Project

Run the following commands to run the project.
- export FLASK_APP=__init__.py
- flask run
