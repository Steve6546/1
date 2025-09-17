# -*- coding: utf-8 -*-
"""
Flask Server for Telegram Tools Bot

This server provides the backend functionality for the Telegram bot.
It handles requests from the bot to process images, videos, and other files.
"""

from flask import Flask, request, jsonify, send_from_directory
import os
from tools import image, video, file as file_tools, other
import logging
import traceback

# Setup logging
logging.basicConfig(filename='error.log', level=logging.ERROR,
                    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

app = Flask(__name__)

# Temporary file storage folder
STATIC_FOLDER = 'static'
if not os.path.exists(STATIC_FOLDER):
    os.makedirs(STATIC_FOLDER)

app.config['UPLOAD_FOLDER'] = STATIC_FOLDER

@app.errorhandler(Exception)
def handle_exception(e):
    """Log exceptions with traceback."""
    app.logger.error(f"An exception occurred: {e}")
    app.logger.error(traceback.format_exc())
    return jsonify({"error": "An internal server error occurred. The error has been logged."}), 500

@app.route('/')
def index():
    """Returns a simple greeting message."""
    return "Hello from Telegram Tools Bot Server!"

@app.route('/game')
def game():
    """Serves the snake game."""
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], 'game'), 'index.html')


if __name__ == '__main__':
    from config import SERVER_HOST, SERVER_PORT
    app.run(host=SERVER_HOST, port=SERVER_PORT)
