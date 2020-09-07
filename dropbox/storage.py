from __future__ import absolute_import
from dropbox import config
from flask import send_file
from google.cloud import storage
from werkzeug import secure_filename
from werkzeug.exceptions import BadRequest
import tempfile


def _get_storage_client():
    return storage.Client(
        project=config.PROJECT_ID)


def _check_extension(filename,allowed_extensions):
    if('.' not in filename or filename.split('.').pop().lower() not in allowed_extensions):
        raise BadRequest("{0} has an invalid name or extension".format(filename))
    return True


def _safe_filename(filename, directory, username):
    filename = secure_filename(filename)
    filename_final = username + '/' + directory + '/' + filename
    return filename_final


def upload_file(file_stream, filename, content_type, directory, username):
    """
    Uploads a file to a given Cloud Storage bucket and returns the file size.
    """
    _check_extension(filename, config.ALLOWED_EXTENSTIONS)
    filename = _safe_filename(filename, directory, username)

    client = _get_storage_client()
    bucket = client.bucket(config.CLOUD_STORAGE_BUCKET)
    blob = bucket.blob(filename)

    blob.upload_from_string(
        file_stream,
        content_type=content_type)

    size = blob.size
    return size

def delete_blob(blob_name):
    """Deletes a file from the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(config.CLOUD_STORAGE_BUCKET)
    blob = bucket.blob(blob_name)
    blob.delete()
    return True

def download_blob(source_blob_name, destination_file_name):
    """Downloads a file from the bucket."""
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(config.CLOUD_STORAGE_BUCKET)
    blob = bucket.blob(source_blob_name)
    with tempfile.NamedTemporaryFile() as temp:
            blob.download_to_filename(temp.name)
            return send_file(temp.name, as_attachment=True, attachment_filename=destination_file_name)

def rename_file(blob_name, new_name):
    """Renames a file."""
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(config.CLOUD_STORAGE_BUCKET)
    blob = bucket.blob(blob_name)
    bucket.rename_blob(blob, new_name)
    return True