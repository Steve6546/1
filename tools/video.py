# -*- coding: utf-8 -*-
"""
Video processing tools for the Telegram bot.
"""

from flask import jsonify, send_from_directory
import yt_dlp
import ffmpeg
import os

def download_video(app, video_url):
    """Downloads a video from a given URL."""
    if not video_url:
        return jsonify({"error": "No URL provided"}), 400

    ydl_opts = {
        'outtmpl': os.path.join(app.config['UPLOAD_FOLDER'], '%(title)s.%(ext)s'),
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)
            return send_from_directory(app.config['UPLOAD_FOLDER'], os.path.basename(filename))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def to_mp3(app, file):
    """Converts a video file to MP3."""
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)

        output_filename = f"{os.path.splitext(filename)[0]}.mp3"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)

        try:
            ffmpeg.input(input_path).output(output_path).run()
            return send_from_directory(app.config['UPLOAD_FOLDER'], output_filename)
        except ffmpeg.Error as e:
            return jsonify({"error": e.stderr.decode('utf8')}), 500
