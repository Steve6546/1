# -*- coding: utf-8 -*-
"""
Other miscellaneous tools for the Telegram bot.
"""

from flask import jsonify, send_from_directory
import qrcode
import os

def generate_qr(app, text):
    """Generates a QR code from text."""
    if not text:
        return jsonify({"error": "No text provided"}), 400

    img = qrcode.make(text)
    filename = "qr_code.png"
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img.save(path)

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
