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
    """Removes the background from an image using the rembg library.

    Args:
        app: The Flask application instance.
        file: The image file to process.

    Returns:
        A Flask response with the processed image or a JSON error message.
    """
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
    """Upscales an image to 4K using the Real-ESRGAN model.

    This function requires the 'realesrgan-ncnn-vulkan' command-line tool
    to be installed and available in the system's PATH.

    Args:
        app: The Flask application instance.
        file: The image file to upscale.

    Returns:
        A Flask response with the upscaled image or a JSON error message.
    """
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
    """Generates a preview of a cropped image with a red border.

    This is used to show the user the result of the interactive crop
    before they confirm the final crop.

    Args:
        app: The Flask application instance.
        filepath (str): The path to the image to be previewed.
        left (int): The x-coordinate of the top-left corner.
        top (int): The y-coordinate of the top-left corner.
        right (int): The x-coordinate of the bottom-right corner.
        bottom (int): The y-coordinate of the bottom-right corner.

    Returns:
        A Flask response with the preview image.
    """
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
    """Crops an image to the specified dimensions.

    Args:
        app: The Flask application instance.
        file: The image file to crop.
        left (int): The x-coordinate of the top-left corner.
        top (int): The y-coordinate of the top-left corner.
        right (int): The x-coordinate of the bottom-right corner.
        bottom (int): The y-coordinate of the bottom-right corner.

    Returns:
        A Flask response with the cropped image or a JSON error message.
    """
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
