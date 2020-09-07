from dropbox import storage, helper_functions
from flask import Blueprint, current_app, redirect, render_template, request, url_for, flash, session, send_file, Markup
from dropbox import model_firestore
import datetime
from firebase_admin import firestore
import os
from werkzeug import secure_filename
import google.cloud



crud = Blueprint('crud',__name__)





@crud.route('/register', methods=['GET','POST'])
def adduser(message = None):
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        db = model_firestore.get_client()
        user_ref = db.collection('users').document(username)
        user_ref.set({
            'name':name,
            'username':username,
            'password':password,
            'folders': 0,
            'files': 0,
            'total_storage_used': 0,
        })
        root_folder_ref = user_ref.collection('folders').document('rootdocument')
        root_folder_ref.set({
            'name': 'root',
            'parent': 'None',
            'owner': username,
            'created_date': datetime.datetime.now(),
            'folders': 0,
            'files': 0,
        })
        return render_template('adduser.html',message='user added')
    return render_template('adduser.html',message=message)


@crud.route('/logon', methods=['GET','POST'])
def logon():
    if 'username' in session:
        returnURL = '/' + session['username']
        return redirect(returnURL)
    if request.method == 'POST':
        username = request.form['email']
        password = request.form['password']
        user_login_status = helper_functions.check_user_existance(username,password)
        if user_login_status == 0:
            session['username'] = username
            url = '/' + username
            return redirect(url)
        elif user_login_status == 1:
            message = "Invalid Password"
            return render_template('logon.html',message = message)
        elif user_login_status == 2:
            message = "User does not exist. Register to login."
            return render_template('adduser.html', message = message)
    return render_template('logon.html')

@crud.route('/<username>/usage', methods=['GET'])
def usage(username):
    db = model_firestore.get_client()
    user_ref = db.collection('users').document(username)
    user_data = user_ref.get().to_dict()
    folders = user_data['folders']
    files = user_data['files']
    total_storage_used = user_data['total_storage_used']
    return render_template('usage.html', files = files, folders = folders, total_storage_used = total_storage_used, username = username)



@crud.route('/logout', methods=['GET','POST'])
def logout():
    if 'username' in session:
        session.pop('username', None)
        return render_template('logon.html', message = "Logged out")
    else:
        return render_template('logon.html', message = None)




@crud.route('/<username>/', methods=['GET','POST'])
def getuserhome(username):
    if helper_functions.user_logged_in() and session['username'] == username:
        db = model_firestore.get_client()
        user_ref = db.collection('users').document(username)
        current_folder_parent = 'None'
        current_folder_id = 'rootdocument'
        directory = current_folder_id
        current_folder_ref = user_ref.collection('folders').document(current_folder_id)
        message = None
        if 'movefile' in session:
            moveFileStatus = True
            movemessage = "Navigate to the folder and click move here to move the file."
        else:
            moveFileStatus = None
            movemessage = None
        if request.method == 'POST':
            if 'CreateNewFolder' in request.form:
                folderName = request.form['folderName']
                createFolderStatus = helper_functions.addNewFolder(folderName, username, user_ref, current_folder_id, current_folder_ref)
                if createFolderStatus == 0:
                    message = "Folder added successfully."
                elif createFolderStatus == 1:
                    message = "Folder name cannot be blank."
                elif createFolderStatus == 2:
                    message = "Duplicate folder exists."

            elif 'UploadNewFile' in request.form:
                if 'fileUpload' not in request.files:
                    flash('No file part')
                    message = "No file uploaded."
                else:
                    file = request.files['fileUpload']
                    # if user does not select file, browser also
                    # submit an empty part without filename
                    if file.filename == '':
                        message = "Please select a file to upload."
                    else:
                        fileUploadStatus = helper_functions.uploadNewFile(file, username, user_ref, current_folder_id, current_folder_ref, request.files)
                        if fileUploadStatus == 3:
                            message = "Duplicate file exists."
                        if fileUploadStatus == 2:
                            message = "Invalid file type. Please upload an image or a text file."
                        elif fileUploadStatus == 0:
                            message = "File uploaded successfully."
                        elif fileUploadStatus == 1:
                            message = "Duplicate file exists. File could not be uploaded."
                        else:
                            duplicate_file_ref = user_ref.collection('files').document(fileUploadStatus)
                            duplicate_file_data = duplicate_file_ref.get().to_dict()
                            duplicate_folder_id = duplicate_file_data['parent']
                            duplicate_folder_ref = user_ref.collection('folders').document(duplicate_folder_id)
                            duplicate_folder_data = duplicate_folder_ref.get().to_dict()
                            if duplicate_folder_id == 'rootdocument':
                                duplicate_folder_name = 'Home'
                                duplicate_folder_url = '/' + username + '/'
                            else:
                                duplicate_folder_name = duplicate_folder_data['name']
                                duplicate_folder_url = '/' + username + '/' + duplicate_folder_id
                            message = Markup("Duplicate file exists in folder <a href='" + duplicate_folder_url + "'>" + duplicate_folder_name + "</a>.")
            elif 'MoveFileHere' in request.form:
                if 'movefile' in session and 'movefrom' in session:
                    move_from_folder_id = session['movefrom']
                    file_id = session['movefile']
                    fileMoveStatus = helper_functions.moveFile(username, user_ref, current_folder_id, move_from_folder_id, file_id)
                    if 'movefile' in session:
                        moveFileStatus = True
                    else:
                        moveFileStatus = None
                else:
                    message = "Invalid file move."
                    session.pop('movefile', None)
                    session.pop('movefrom', None)
            current_folder = current_folder_ref.get().to_dict()
            sub_folder_ids = helper_functions.getSubFolderIDs(current_folder)
            file_ids = helper_functions.getSubFileIDs(current_folder)
            folders_data = helper_functions.get_folders(user_ref,current_folder)
            files_data = helper_functions.get_files(user_ref, current_folder)

            #get breadcrumbs for current directory
            breadcrumbs = helper_functions.get_breadcrumb(username, directory)

            return render_template('folders.html', username = username, directory = directory, folders = folders_data, folder_ids = sub_folder_ids, files = files_data, file_ids = file_ids, bc_folders = breadcrumbs, moveFileStatus = moveFileStatus,  movemessage = movemessage, message = message)
        else:
            action = request.args.get("action")
            if action == 'deletefile':
                file_id = request.args.get("file")
                if file_id is None:
                    messsage = "Invalid file to delete."
                else:
                    deleteFileStatus = helper_functions.deleteFile(username, user_ref,current_folder_ref, file_id)
                    if deleteFileStatus == 2:
                        message = "File deleted from invalid folder."
                    elif deleteFileStatus == 0:
                        message = "File deleted successfully."
            if action == 'deletefolder':
                folder_id = request.args.get("folder")
                if folder_id is None:
                    messsage = "Invalid folder to delete."
                else:
                    deleteFolderStatus = helper_functions.deleteFolder(username, user_ref,current_folder_ref, folder_id)
                    if deleteFolderStatus == 2:
                        message = "Folder deleted from invalid parent folder."
                    elif deleteFolderStatus == 1:
                        message = "Folder not empty. Cannot be deleted."
                    elif deleteFolderStatus == 0:
                        message = "Folder deleted successfully."
            if action == 'download':
                file_id = request.args.get("file")
                if file_id is None:
                    message = "No file to download."
                else:
                    fileDownloadStatus = helper_functions.downloadFile(username, user_ref, current_folder_ref, file_id)
                    if fileDownloadStatus  == 2:
                        message = "File downloaded from invalid folder."
                    else:
                        return fileDownloadStatus
            if action == 'movefile':
                movefrom = request.args.get("from")
                movefile = request.args.get("file")
                if movefrom is None or movefile is None:
                    messsage = "Invalid folder of file."
                else:
                    session.pop('movefile', None)
                    session.pop('movefrom', None)
                    session['movefile'] = movefile
                    session['movefrom'] = movefrom
                    moveFileStatus = True
                    movemessage = "Navigate to the folder and click move here to move the file."
            current_folder = current_folder_ref.get().to_dict()
            sub_folder_ids = helper_functions.getSubFolderIDs(current_folder)
            file_ids = helper_functions.getSubFileIDs(current_folder)
            folders_data = helper_functions.get_folders(user_ref,current_folder)
            files_data = helper_functions.get_files(user_ref, current_folder)

            #get breadcrumbs for current directory
            breadcrumbs = helper_functions.get_breadcrumb(username, directory)

            return render_template('folders.html', username = username, directory = directory, folders = folders_data, folder_ids = sub_folder_ids, files = files_data, file_ids = file_ids, bc_folders = breadcrumbs, moveFileStatus = moveFileStatus,  movemessage = movemessage, message = message)
    else:
        return redirect('/logon')


@crud.route('/<username>/<directory>', methods=['GET','POST'])
def getfolder(username, directory):
    directory = directory.rstrip('/')
    if helper_functions.user_logged_in() and session['username'] == username:
        db = model_firestore.get_client()
        user_ref = db.collection('users').document(username)
        if not helper_functions.directory_exists(user_ref,directory):
            returnURL = '/' + username
            return redirect(returnURL)
        current_folder_id = directory
        current_folder_ref = user_ref.collection('folders').document(current_folder_id)
        current_folder = current_folder_ref.get().to_dict()
        current_folder_parent = current_folder['parent']
        message = None
        if 'movefile' in session:
            moveFileStatus = True
            movemessage = "Navigate to the folder and click move here to move the file."
        else:
            moveFileStatus = None
            movemessage = None
        if request.method == 'POST':
            if 'CreateNewFolder' in request.form:
                folderName = request.form['folderName']
                createFolderStatus = helper_functions.addNewFolder(folderName, username, user_ref, current_folder_id, current_folder_ref)
                if createFolderStatus == 0:
                    message = "Folder added successfully."
                elif createFolderStatus == 1:
                    message = "Folder name cannot be blank."
                elif createFolderStatus == 2:
                    message = "Duplicate folder exists."

            elif 'UploadNewFile' in request.form:
                if 'fileUpload' not in request.files:
                    flash('No file part')
                    message = "No file uploaded."
                else:
                    file = request.files['fileUpload']
                    # if user does not select file, browser also
                    # submit an empty part without filename
                    if file.filename == '':
                        message = "Please select a file to upload."
                    else:
                        fileUploadStatus = helper_functions.uploadNewFile(file, username, user_ref, current_folder_id, current_folder_ref, request.files)
                        if fileUploadStatus == 2:
                            message = "Invalid file type. Please upload an image or a text file."
                        elif fileUploadStatus == 0:
                            message = "File uploaded successfully."
                        elif fileUploadStatus == 1:
                            message = "Duplicate file exists. File could not be uploaded."
                        else:
                            duplicate_file_ref = user_ref.collection('files').document(fileUploadStatus)
                            duplicate_file_data = duplicate_file_ref.get().to_dict()
                            duplicate_folder_id = duplicate_file_data['parent']
                            duplicate_folder_ref = user_ref.collection('folders').document(duplicate_folder_id)
                            duplicate_folder_data = duplicate_folder_ref.get().to_dict()
                            if duplicate_folder_id == 'rootdocument':
                                duplicate_folder_name = 'Home'
                                duplicate_folder_url = '/' + username + '/'
                            else:
                                duplicate_folder_name = duplicate_folder_data['name']
                                duplicate_folder_url = '/' + username + '/' + duplicate_folder_id
                            message = Markup("Duplicate file exists in folder <a href='" + duplicate_folder_url + "'>" + duplicate_folder_name + "</a>.")
            elif 'MoveFileHere' in request.form:
                if 'movefile' in session and 'movefrom' in session:
                    move_from_folder_id = session['movefrom']
                    file_id = session['movefile']
                    fileMoveStatus = helper_functions.moveFile(username, user_ref, current_folder_id, move_from_folder_id, file_id)
                    if 'movefile' in session:
                        moveFileStatus = True
                    else:
                        moveFileStatus = None
                        message = "File moved successfully."
                else:
                    message = "Invalid file move."
                    session.pop('movefile', None)
                    session.pop('movefrom', None)
            current_folder = current_folder_ref.get().to_dict()
            sub_folder_ids = helper_functions.getSubFolderIDs(current_folder)
            file_ids = helper_functions.getSubFileIDs(current_folder)
            folders_data = helper_functions.get_folders(user_ref,current_folder)
            files_data = helper_functions.get_files(user_ref, current_folder)

            #get breadcrumbs for current directory
            breadcrumbs = helper_functions.get_breadcrumb(username, directory)
            return render_template('folders.html', username = username, folders = folders_data, folder_ids = sub_folder_ids, directory = directory, files = files_data, file_ids = file_ids, bc_folders = breadcrumbs, moveFileStatus = moveFileStatus,  movemessage = movemessage, message = message)
        else:
            action = request.args.get("action")
            if action == 'deletefile':
                file_id = request.args.get("file")
                if file_id is None:
                    messsage = "Invalid file to delete."
                else:
                    deleteFileStatus = helper_functions.deleteFile(username, user_ref,current_folder_ref, file_id)
                    if deleteFileStatus == 2:
                        message = "File deleted from invalid folder."
                    elif deleteFileStatus == 0:
                        message = "File deleted successfully."
            if action == 'deletefolder':
                folder_id = request.args.get("folder")
                if folder_id is None:
                    messsage = "Invalid folder to delete."
                else:
                    deleteFolderStatus = helper_functions.deleteFolder(username, user_ref,current_folder_ref, folder_id)
                    if deleteFolderStatus == 2:
                        message = "Folder deleted from invalid parent folder."
                    elif deleteFolderStatus == 1:
                        message = "Folder not empty. Cannot be deleted."
                    elif deleteFolderStatus == 0:
                        message = "Folder deleted successfully."
            if action == 'download':
                file_id = request.args.get("file")
                if file_id is None:
                    message = "No file to download."
                else:
                    fileDownloadStatus = helper_functions.downloadFile(username, user_ref, current_folder_ref, file_id)
                    if fileDownloadStatus  == 2:
                        message = "File downloaded from invalid folder."
                    else:
                        return fileDownloadStatus
            if action == 'movefile':
                movefrom = request.args.get("from")
                movefile = request.args.get("file")
                if movefrom is None or movefile is None:
                    messsage = "Invalid folder of file."
                else:
                    session.pop('movefile', None)
                    session.pop('movefrom', None)
                    session['movefile'] = movefile
                    session['movefrom'] = movefrom
                    moveFileStatus = True
                    movemessage = "Navigate to the folder and click move here to move the file."

            current_folder = current_folder_ref.get().to_dict()
            sub_folder_ids = helper_functions.getSubFolderIDs(current_folder)
            file_ids = helper_functions.getSubFileIDs(current_folder)
            folders_data = helper_functions.get_folders(user_ref,current_folder)
            files_data = helper_functions.get_files(user_ref, current_folder)

            #get breadcrumbs for current directory
            breadcrumbs = helper_functions.get_breadcrumb(username, directory)

            return render_template('folders.html', username = username, folders = folders_data, folder_ids = sub_folder_ids,  directory = directory, files = files_data, file_ids = file_ids, bc_folders = breadcrumbs, moveFileStatus = moveFileStatus, movemessage = movemessage, message = message)
    else:
        return redirect('/logon')

@crud.route('/<username>/<directory>/upload', methods=['GET','POST'])
def uploadFileToFolder(username, directory):
    db = model_firestore.get_client()
    user_ref = db.collection('users').document(username)
    if directory == 'rootdocument':
        returnURL = '/' + username + '/'
    else:
        returnURL = '/' + username + '/' + directory
    folder_upload_ref = user_ref.collection('folders').document(directory)
    if request.method == 'POST':
        if 'fileUpload' not in request.files:
            flash('No file part')
            return redirect(returnURL)
        file = request.files['fileUpload']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(returnURL)
        fileName = secure_filename(file.filename)
        if helper_functions.duplicate_file_exists(fileName, directory, username):
            return redirect(returnURL)
        data = request.form.to_dict(flat=True)
        fileSize = helper_functions.upload_file(request.files.get('fileUpload'), directory, username)
        if fileSize:
            file_extension = fileName.split('.')[1]
            fileType = helper_functions.get_file_type(file_extension)
            file_ref = user_ref.collection('files').document()
            file_ref.set({
                'name': fileName,
                'owner': username,
                'size': fileSize,
                'type': fileType,
                'parent': folder_upload_ref.id,
                'created_date': datetime.datetime.now(),
            })
            folder_upload_ref.update({'files': firestore.ArrayUnion([file_ref.id])})
        return redirect(returnURL)
    else:
        return redirect(returnURL)

@crud.route('/<username>/upload', methods=['GET','POST'])
def uploadFileToRootFolder(username):
    db = model_firestore.get_client()
    user_ref = db.collection('users').document(username)
    directory = 'rootdocument'
    returnURL = '/' + username + '/'
    folder_upload_ref = user_ref.collection('folders').document(directory)
    if request.method == 'POST':
        if 'fileUpload' not in request.files:
            flash('No file part')
            return redirect(returnURL)
        file = request.files['fileUpload']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(returnURL)
        fileName = secure_filename(file.filename)
        if helper_functions.duplicate_file_exists(fileName, directory, username):
            return redirect(returnURL)
        data = request.form.to_dict(flat=True)
        fileSize = helper_functions.upload_file(request.files.get('fileUpload'), directory, username)
        if fileSize:
            file_extension = fileName.split('.')[1]
            fileType = helper_functions.get_file_type(file_extension)
            file_ref = user_ref.collection('files').document()
            file_ref.set({
                'name': fileName,
                'owner': username,
                'size': fileSize,
                'type': fileType,
                'parent': folder_upload_ref.id,
                'created_date': datetime.datetime.now(),
            })
            folder_upload_ref.update({'files': firestore.ArrayUnion([file_ref.id])})
        return redirect(returnURL)
    else:
        return redirect(returnURL)
