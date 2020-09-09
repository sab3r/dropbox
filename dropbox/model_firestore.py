from flask import current_app
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from dropbox import config

# Use the application default credentials
cred = credentials.ApplicationDefault()
firebase_admin.initialize_app(cred, {
    'projectId': config.PROJECT_ID,
})

def init_app(app):
    pass

def get_client():
    return firestore.Client()
