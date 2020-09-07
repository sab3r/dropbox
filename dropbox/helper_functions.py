from dropbox import storage
from flask import Blueprint, current_app, redirect, render_template, request, url_for, flash, session, send_file, Markup
from dropbox import model_firestore
import datetime
from firebase_admin import firestore
import os
from werkzeug import secure_filename
import google.cloud

def upload_file(file, directory, username):
    if not file:
        return None
    fileSize = storage.upload_file(file.read(), file.filename, file.content_type, directory, username)
    #current_app.logger.info("Uploaded file %s as %s", file.filename, public_url)
    return fileSize



def user_logged_in():
    if 'username' in session:
        return True
    else:
        return False

def check_user_existance(username,password):
    #if user exists in firestore return True
    db = model_firestore.get_client()
    user_ref = db.collection('users').document(username)
    user = user_ref.get()
    user_data = user_ref.get().to_dict()
    if user_data:
        if username == user_data['username'] and password == user_data['password']:
            return 0
        else:
            return 1
    else:
        return 2

def addNewFolder(folderName, username, user_ref, current_folder_id, current_folder_ref):
    if duplicate_folder_exists(folderName, current_folder_id, username):
        return 2
    elif folderName == "":
        return 1
    else:
        folder_ref = user_ref.collection('folders').document()
        folder_ref.set({
            'name':folderName,
            'owner':username,
            'parent':current_folder_id,
            'created_date': datetime.datetime.now(),
        })
        current_folder_ref.update({
            'folders':firestore.ArrayUnion([folder_ref.id])
        })
        user_data = user_ref.get().to_dict()
        updatedFolderCount = int(user_data['folders']) + 1
        user_ref.update({
            'folders': updatedFolderCount
        })
        return 0

def uploadNewFile(file, username, user_ref, current_folder_id, current_folder_ref, fileRequest):
    fileName = secure_filename(file.filename)
    duplicate_file_id = check_duplicate_file(fileName, user_ref)
    if duplicate_file_id:
        return duplicate_file_id
    display_fileName = file.filename
    file_extension = fileName.split('.')[1]
    fileType = get_file_type(file_extension)
    if fileType == 'None':
        return 2
    if duplicate_file_exists(fileName, current_folder_id, username):
        return 1
    fileSize = upload_file(fileRequest.get('fileUpload'), current_folder_id, username)
    if fileSize:
        file_ref = user_ref.collection('files').document()
        file_ref.set({
            'name': fileName,
            'display_name': display_fileName,
            'owner': username,
            'size': fileSize,
            'type': fileType,
            'parent': current_folder_id,
            'created_date': datetime.datetime.now(),
        })
        current_folder_ref.update({'files': firestore.ArrayUnion([file_ref.id])})
        user_data = user_ref.get().to_dict()
        updatedFilesCount = int(user_data['files']) + 1
        user_ref.update({
            'files': updatedFilesCount
        })
        updatedStorageUsed = int(user_data['total_storage_used']) + fileSize
        user_ref.update({
            'total_storage_used': updatedStorageUsed
        })
        return 0
    return 1


def moveFile(username, user_ref, current_folder_id, move_from_folder_id, file_id):
    file_ref = user_ref.collection('files').document(file_id)
    move_from_folder_ref = user_ref.collection('folders').document(move_from_folder_id)
    current_folder_ref = user_ref.collection('folders').document(current_folder_id)
    file_data = file_ref.get().to_dict()
    current_file_parent = file_data['parent']
    file_name = file_data['name']
    if current_file_parent == move_from_folder_id:
        storage_current_file_name = username + '/' + current_file_parent + '/' + file_name
        storage_new_file_name = username + '/' + current_folder_id + '/' + file_name
        if duplicate_file_exists(file_name, current_folder_id, username):
            return 1 #duplicate file exists in new folder. Cannot move file.
        else:
            move_from_folder_ref.update({'files': firestore.ArrayRemove([file_id])})
            current_folder_ref.update({'files': firestore.ArrayUnion([file_id])})
            file_ref.update({'parent': current_folder_id})
            storage.rename_file(storage_current_file_name, storage_new_file_name)
            session.pop('movefrom', None)
            session.pop('movefile', None)
    else:
        return 2 # move from and file parent do not match


def getSubFileIDs(current_folder):
    if 'files' in current_folder:
        if len(current_folder['files']) == 0:
            return None
        else:
            return current_folder['files']
    else:
        return None

def getSubFolderIDs(current_folder):
    if 'folders' in current_folder:
        if len(current_folder['folders']) == 0:
            return None
        else:
            return current_folder['folders']
    else:
        return None

def get_folders(user_ref, current_folder):
    if 'folders' in current_folder:
        if len(current_folder['folders']) == 0:
            return None
        else:
            sub_folder_ids = current_folder['folders']
            folders_data = [user_ref.collection('folders').document(folder).get().to_dict() for folder in sub_folder_ids]
            return folders_data
    else:
        return None

def get_files(user_ref, current_folder):
    if 'files' in current_folder:
        if len(current_folder['files']) == 0:
            return None
        else:
            sub_files_ids = current_folder['files']
            files_data = [user_ref.collection('files').document(files).get().to_dict() for files in sub_files_ids]
            return files_data
    else:
        return None



def deleteFolder(username, user_ref,current_folder_ref, folder_id):
    folder_delete_ref = user_ref.collection('folders').document(folder_id)
    folder_data = folder_delete_ref.get().to_dict()
    folder_parent_id = folder_data['parent']
    if not folder_parent_id == current_folder_ref.id:
        return 2
    if folder_empty(username, folder_id):
        folder_delete_ref.delete()
        current_folder_ref.update({'folders': firestore.ArrayRemove([folder_id])})
        user_data = user_ref.get().to_dict()
        totalFolders = int(user_data['folders']) - 1
        user_ref.update({
            'folders': totalFolders,
        })
        return 0
    else:
        return 1

def deleteFile(username, user_ref, current_folder_ref, file_id):
    #directory = directory.rstrip('/')
    file_delete_ref = user_ref.collection('files').document(file_id)
    file_data = file_delete_ref.get().to_dict()
    file_parent_id = file_data['parent']
    if not current_folder_ref.id == file_parent_id:
        return 2
    if user_logged_in() and session['username'] == username:
        filename = username + '/' + file_parent_id + '/' + file_data['name']
        storage.delete_blob(filename)
        file_delete_ref.delete()
        current_folder_ref.update({'files': firestore.ArrayRemove([file_id])})
        user_data = user_ref.get().to_dict()
        totalFiles = int(user_data['files']) - 1
        totalStorageUsed = int(user_data['total_storage_used']) - file_data['size']
        user_ref.update({
            'files': totalFiles,
            'total_storage_used': totalStorageUsed,
        })
        return 0


def get_file_type(file_extension):
    if file_extension.upper() in ['JPG', 'PNG', 'GIF', 'JPEG']:
        return 'Image'
    elif file_extension.upper() in ['TXT']:
        return 'Text'
    else:
        return 'None'

def duplicate_folder_exists(folderName, directory, username):
    if user_logged_in() and session['username'] == username:
        db = model_firestore.get_client()
        user_ref = db.collection('users').document(username)
        folder_ref = user_ref.collection('folders').document(directory)
        folder_data = folder_ref.get().to_dict()
        if 'folders' in folder_data:
            if len(folder_data['folders']) == 0:
                return False
            else:
                for folder in folder_data['folders']:
                    sub_folder_ref = user_ref.collection('folders').document(folder)
                    sub_folder_data = sub_folder_ref.get().to_dict()
                    if folderName == sub_folder_data['name']:
                        return True
                return False
        else:
            return False

def duplicate_file_exists(fileName, directory, username):
    if user_logged_in() and session['username'] == username:
        db = model_firestore.get_client()
        user_ref = db.collection('users').document(username)
        folder_ref = user_ref.collection('folders').document(directory)
        folder_data = folder_ref.get().to_dict()
        if 'files' in folder_data:
            if len(folder_data['files']) == 0:
                return False
            else:
                for files in folder_data['files']:
                    sub_file_ref = user_ref.collection('files').document(files)
                    sub_file_data = sub_file_ref.get().to_dict()
                    if fileName == sub_file_data['name']:
                        return True
                return False
        else:
            return False



def folder_empty(username, directory):
    if user_logged_in() and session['username'] == username:
        db = model_firestore.get_client()
        user_ref = db.collection('users').document(username)
        folder_ref = user_ref.collection('folders').document(directory)
        folder_data = folder_ref.get().to_dict()
        if 'folders' in folder_data:
            if len(folder_data['folders']) == 0:
                #check for files
                if 'files' in folder_data:
                    if len(folder_data['files']) == 0:
                        return True
                    else:
                        return False
                else:
                    return True
            else:
                return False
        else:
            if 'files' in folder_data:
                if len(folder_data['files']) == 0:
                    return True
                else:
                    return False
            else:
                return True


def downloadFile(username, user_ref, current_folder_ref, file_id):
    file_ref = user_ref.collection('files').document(file_id)
    file_data = file_ref.get().to_dict()
    fileParent = file_data['parent']
    if not fileParent == current_folder_ref.id:
        return 2
    else:
        fileName = file_data['name']
        source_name = username + '/' + fileParent + '/' + fileName
        destination_name = file_data['display_name']
        file_data = storage.download_blob(source_name, destination_name)
        return file_data


def get_breadcrumb(username, folder_id):
    db = model_firestore.get_client()
    user_ref = db.collection('users').document(username)
    folder_ref = user_ref.collection('folders').document(folder_id)
    folder_data = folder_ref.get().to_dict()
    i = 0
    breadcrumbs = []
    if folder_ref.id == 'rootdocument':
        return breadcrumbs
    current_folder_data = [folder_id, folder_data['name']]
    folder_parent = folder_data['parent']
    breadcrumbs.insert(0, current_folder_data)
    while not folder_parent == 'rootdocument':
        folder_ref = user_ref.collection('folders').document(folder_data['parent'])
        folder_id = folder_ref.id
        folder_data = folder_ref.get().to_dict()
        current_folder_data = [folder_id, folder_data['name']]
        folder_parent = folder_data['parent']
        breadcrumbs.insert(0, current_folder_data)
    return breadcrumbs

def check_duplicate_file(fileName, user_ref):
    files = user_ref.collection('files').where('name', '==', fileName).stream()
    files_ids = [duplicate_file.id for duplicate_file in files]
    if len(files_ids) == 0:
        return False
    else:
        return files_ids[0]
def directory_exists(user_ref,directory):
    folder_ref = user_ref.collection('folders').document(directory)
    folder_data = folder_ref.get().to_dict()
    if folder_data:
        return True
    else:
        return False