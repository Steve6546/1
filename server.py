# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify, send_from_directory
import os
import subprocess
from werkzeug.utils import secure_filename
from rembg import remove
from PIL import Image
import yt_dlp
import ffmpeg
import qrcode
import zipfile
import shutil

app = Flask(__name__)

# مجلد لتخزين الملفات المؤقتة
STATIC_FOLDER = 'static'
if not os.path.exists(STATIC_FOLDER):
    os.makedirs(STATIC_FOLDER)

app.config['UPLOAD_FOLDER'] = STATIC_FOLDER

@app.route('/')
def index():
    return "Hello from Telegram Tools Bot Server!"

@app.route('/handle_tool', methods=['POST'])
def handle_tool():
    data = request.get_json()
    tool = data.get('tool')

    if tool == 'remove_bg':
        message = "أرسل لي صورة لإزالة خلفيتها."
    elif tool == 'download_video':
        message = "أرسل لي رابط الفيديو الذي تريد تحميله."
    elif tool == 'to_mp3':
        message = "أرسل لي ملف الفيديو لتحويله إلى MP3."
    elif tool == 'generate_qr':
        message = "أرسل لي النص أو الرابط الذي تريد تحويله إلى QR code."
    elif tool == 'zip_file':
        message = "أرسل لي الملفات التي تريد ضغطها."
    elif tool == 'unzip_file':
        message = "أرسل لي ملف ZIP لفك ضغطه."
    elif tool == 'upscale_4k':
        message = "أرسل لي صورة لتحسينها بدقة 4K."
    elif tool == 'crop_image':
        message = "أرسل لي صورة لقصها."
    else:
        message = f"تم اختيار أداة: {tool}. هذه الميزة قيد التطوير."

    return jsonify({"message": message})

@app.route('/remove_bg', methods=['POST'])
def remove_bg():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
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


@app.route('/download_video', methods=['POST'])
def download_video():
    data = request.get_json()
    video_url = data.get('url')

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

@app.route('/to_mp3', methods=['POST'])
def to_mp3():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
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

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    data = request.get_json()
    text = data.get('text')

    if not text:
        return jsonify({"error": "No text provided"}), 400

    img = qrcode.make(text)
    filename = "qr_code.png"
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    img.save(path)

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/zip_file', methods=['POST'])
def zip_file():
    if 'files' not in request.files:
        return jsonify({"error": "No file part"}), 400
    files = request.files.getlist('files')
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


@app.route('/unzip_file', methods=['POST'])
def unzip_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
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

@app.route('/upscale_4k', methods=['POST'])
def upscale_4k():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
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

@app.route('/crop_image', methods=['POST'])
def crop_image():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        filename = secure_filename(file.filename)
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_path)

        img = Image.open(input_path)
        width, height = img.size
        left = width / 4
        top = height / 4
        right = 3 * width / 4
        bottom = 3 * height / 4
        cropped_img = img.crop((left, top, right, bottom))

        output_filename = f"cropped_{filename}"
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        cropped_img.save(output_path)

        return send_from_directory(app.config['UPLOAD_FOLDER'], output_filename)


if __name__ == '__main__':
    from config import SERVER_HOST, SERVER_PORT
    app.run(host=SERVER_HOST, port=SERVER_PORT)
