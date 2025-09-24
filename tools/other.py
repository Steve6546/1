# -*- coding: utf-8 -*-
"""
Other miscellaneous tools for the Telegram bot.
"""

from flask import jsonify, send_from_directory
import qrcode
import os

def generate_qr(app, text):
    """Generates a QR code image from the provided text.

    Args:
        app: The Flask application instance.
        text (str): The text or URL to encode in the QR code.

    Returns:
        A Flask response with the generated QR code image or a JSON error message.
    """
    if not text:
        return jsonify({"error": "No text provided"}), 400

    img = qrcode.make(text)
    filename = "qr_code.png"
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img.save(path)

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
