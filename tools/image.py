# -*- coding: utf-8 -*-
"""
Image processing tools for the Telegram bot.
"""

from flask import jsonify, send_from_directory
from werkzeug.utils import secure_filename
from rembg import remove
from PIL import Image
import os
import subprocess

def remove_bg(app, file):
    """Removes the background from an image."""
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)

        output_filename = f"removed_bg_{filename}"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

        with open(input_path, 'rb') as i:
            with open(output_path, 'wb') as o:
                input_data = i.read()
                output_data = remove(input_data)
                o.write(output_data)

        return send_from_directory(app.config['UPLOAD_FOLDER'], output_filename)

def upscale_4k(app, file):
    """Upscales an image to 4K using Real-ESRGAN."""
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)

        output_filename = f"upscaled_{filename}"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

        try:
            subprocess.run(['realesrgan-ncnn-vulkan', '-i', input_path, '-o', output_path], check=True)
            return send_from_directory(app.config['UPLOAD_FOLDER'], output_filename)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            return jsonify({"error": "Real-ESRGAN not found or failed to process image."}), 500

def preview_crop(app, filepath, left, top, right, bottom):
    """Generates a preview of the cropped image."""
    img = Image.open(filepath)
    # Add a red border to the preview
    preview_img = Image.new('RGB', img.size, (255, 0, 0))
    preview_img.paste(img, (0, 0))

    cropped_preview = preview_img.crop((left, top, right, bottom))

    preview_filename = f"preview_{os.path.basename(filepath)}"
    preview_path = os.path.join(app.config['UPLOAD_FOLDER'], preview_filename)
    cropped_preview.save(preview_path)

    return send_from_directory(app.config['UPLOAD_FOLDER'], preview_filename)

def crop_image(app, file, left, top, right, bottom):
    """Crops an image with the given dimensions."""
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)

        img = Image.open(input_path)
        cropped_img = img.crop((left, top, right, bottom))

        output_filename = f"cropped_{filename}"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        cropped_img.save(output_path)

        return send_from_directory(app.config['UPLOAD_FOLDER'], output_filename)
