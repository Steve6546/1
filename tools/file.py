# -*- coding: utf-8 -*-
"""
File management tools for the Telegram bot.
"""

from flask import jsonify, send_from_directory
from werkzeug.utils import secure_filename
import zipfile
import shutil
import os

def zip_file(app, files):
    """Zips a list of files."""
    if not files or files[0].filename == '':
        return jsonify({"error": "No selected files"}), 400

    zip_filename = "archive.zip"
    zip_path = os.path.join(app.config['UPLOAD_FOLDER'], zip_filename)

    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in files:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            zipf.write(file_path, filename)
            os.remove(file_path)

    return send_from_directory(app.config['UPLOAD_FOLDER'], zip_filename)

def unzip_file(app, file):
    """Unzips a zip file."""
    if file.filename == '' or not file.filename.endswith('.zip'):
        return jsonify({"error": "Please upload a zip file"}), 400

    filename = secure_filename(file.filename)
    zip_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(zip_path)

    extract_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'unzipped_files')
    if os.path.exists(extract_dir):
        shutil.rmtree(extract_dir)
    os.makedirs(extract_dir)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

    shutil.make_archive(os.path.join(app.config['UPLOAD_FOLDER'], 'unzipped_archive'), 'zip', extract_dir)

    return send_from_directory(app.config['UPLOAD_FOLDER'], 'unzipped_archive.zip')
