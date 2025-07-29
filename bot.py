# -*- coding: utf-8 -*-

import logging
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, ConversationHandler
from config import BOT_TOKEN, SERVER_HOST, SERVER_PORT
import os
import json
import time

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load tools from JSON file
with open('tools.json', 'r', encoding='utf-8') as f:
    TOOLS = json.load(f)

# Conversation states
CHOOSING, WAITING_FOR_IMAGE, WAITING_FOR_URL, WAITING_FOR_VIDEO_FILE, WAITING_FOR_QR_TEXT, WAITING_FOR_FILES_TO_ZIP, WAITING_FOR_ZIP_TO_UNZIP, WAITING_FOR_IMAGE_UPSCALE, WAITING_FOR_IMAGE_CROP, WAITING_FOR_TOOL_DETAILS = range(10)

TOOLS_PER_PAGE = 4

# Anti-spam
user_timestamps = {}
SPAM_LIMIT = 3 # seconds

def is_spam(user_id):
    current_time = time.time()
    if user_id in user_timestamps and current_time - user_timestamps[user_id] < SPAM_LIMIT:
        return True
    user_timestamps[user_id] = current_time
    return False

# Main menu keyboard
def get_main_menu_keyboard(page=0):
    tool_keys = list(TOOLS.keys())
    start_index = page * TOOLS_PER_PAGE
    end_index = start_index + TOOLS_PER_PAGE

    keyboard = []
    for i in range(start_index, end_index, 2):
        row = []
        if i < len(tool_keys):
            key1 = tool_keys[i]
            row.append(InlineKeyboardButton(TOOLS[key1]["name"], callback_data=key1))
        if i + 1 < len(tool_keys):
            key2 = tool_keys[i+1]
            row.append(InlineKeyboardButton(TOOLS[key2]["name"], callback_data=key2))
        keyboard.append(row)

    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"page_{page-1}"))
    if end_index < len(tool_keys):
        pagination_row.append(InlineKeyboardButton("التالي ➡️", callback_data=f"page_{page+1}"))

    if pagination_row:
        keyboard.append(pagination_row)

    keyboard.append([InlineKeyboardButton("ℹ️ تفاصيل الأداة", callback_data='tool_details'), InlineKeyboardButton("🤖 حول البوت", callback_data='about')])
    keyboard.append([InlineKeyboardButton("🗑️ مسح المحادثة", callback_data='clear_chat')])
    return InlineKeyboardMarkup(keyboard)


# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if is_spam(update.effective_user.id): return CHOOSING
    await update.message.reply_text(
        'أهلاً بك في بوت الأدوات! اختر أداة من القائمة:',
        reply_markup=get_main_menu_keyboard()
    )
    return CHOOSING

# Button click handler
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if is_spam(update.effective_user.id): return CHOOSING
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("page_"):
        page = int(data.split("_")[1])
        await query.edit_message_reply_markup(reply_markup=get_main_menu_keyboard(page))
        return CHOOSING

    if data == 'clear_chat':
        await query.edit_message_text("هذه الميزة قيد التطوير.")
        return CHOOSING

    if data == 'about':
        await query.edit_message_text("هذا البوت هو مشروع مفتوح المصدر يهدف إلى توفير أدوات مفيدة لمستخدمي تيليجرام.\n\n"
                                     "يمكنك المساهمة في المشروع على GitHub: [رابط المشروع](https://github.com/your-username/telegram-tools-bot)",
                                     parse_mode='Markdown')
        return CHOOSING

    if data == 'tool_details':
        await query.edit_message_text("اختر أداة لعرض تفاصيلها:", reply_markup=get_tool_details_keyboard())
        return WAITING_FOR_TOOL_DETAILS

    tool = data
    if tool in TOOLS:
        if tool == 'remove_bg':
            await query.edit_message_text(text="أرسل لي صورة لإزالة خلفيتها.")
            return WAITING_FOR_IMAGE
        elif tool == 'download_video':
            await query.edit_message_text(text="أرسل لي رابط الفيديو الذي تريد تحميله.")
            return WAITING_FOR_URL
        elif tool == 'to_mp3':
            await query.edit_message_text(text="أرسل لي ملف الفيديو لتحويله إلى MP3.")
            return WAITING_FOR_VIDEO_FILE
        elif tool == 'generate_qr':
            await query.edit_message_text(text="أرسل لي النص أو الرابط الذي تريد تحويله إلى QR code.")
            return WAITING_FOR_QR_TEXT
        elif tool == 'zip_file':
            await query.edit_message_text(text="أرسل لي الملفات التي تريد ضغطها. أرسل 'تم' عند الانتهاء.")
            context.user_data['files_to_zip'] = []
            return WAITING_FOR_FILES_TO_ZIP
        elif tool == 'unzip_file':
            await query.edit_message_text(text="أرسل لي ملف ZIP لفك ضغطه.")
            return WAITING_FOR_ZIP_TO_UNZIP
        elif tool == 'upscale_4k':
            await query.edit_message_text(text="أرسل لي صورة لتحسينها بدقة 4K.")
            return WAITING_FOR_IMAGE_UPSCALE
        elif tool == 'crop_image':
            await query.edit_message_text(text="أرسل لي صورة لقصها.")
            return WAITING_FOR_IMAGE_CROP
    else:
        await query.edit_message_text(text=f"تم اختيار أداة: {tool}. هذه الميزة قيد التطوير.")
        return CHOOSING

# Image handler
async def image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if is_spam(update.effective_user.id): return WAITING_FOR_IMAGE
    photo_file = await update.message.photo[-1].get_file()
    file_name = f"{photo_file.file_id}.jpg"
    await photo_file.download_to_drive(file_name)

    await update.message.reply_text("جاري معالجة الصورة...")

    try:
        with open(file_name, 'rb') as f:
            response = requests.post(f"http://{SERVER_HOST}:{SERVER_PORT}/remove_bg", files={'file': f})

        if response.status_code == 200:
            processed_image_path = os.path.join('static', f"processed_{file_name}")
            with open(processed_image_path, 'wb') as f:
                f.write(response.content)

            await update.message.reply_photo(photo=open(processed_image_path, 'rb'))
            os.remove(processed_image_path)
        else:
            await update.message.reply_text("حدث خطأ أثناء معالجة الصورة.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to server: {e}")
        await update.message.reply_text("لا يمكن الوصول إلى الخادم حاليًا.")
    finally:
        os.remove(file_name)

    await update.message.reply_text(
        'اختر أداة أخرى:',
        reply_markup=get_main_menu_keyboard()
    )
    return CHOOSING


# URL handler for video download
async def url_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if is_spam(update.effective_user.id): return WAITING_FOR_URL
    video_url = update.message.text
    await update.message.reply_text("جاري تحميل الفيديو...")

    try:
        response = requests.post(f"http://{SERVER_HOST}:{SERVER_PORT}/download_video", json={'url': video_url})

        if response.status_code == 200:
            video_path = os.path.join('static', 'downloaded_video.mp4')
            with open(video_path, 'wb') as f:
                f.write(response.content)

            await update.message.reply_video(video=open(video_path, 'rb'))
            os.remove(video_path)
        else:
            await update.message.reply_text(f"حدث خطأ أثناء تحميل الفيديو: {response.json().get('error')}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to server: {e}")
        await update.message.reply_text("لا يمكن الوصول إلى الخادم حاليًا.")

    await update.message.reply_text(
        'اختر أداة أخرى:',
        reply_markup=get_main_menu_keyboard()
    )
    return CHOOSING

# Video file handler for MP3 conversion
async def video_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if is_spam(update.effective_user.id): return WAITING_FOR_VIDEO_FILE
    video_file = await update.message.video.get_file()
    file_name = video_file.file_path.split('/')[-1]
    await video_file.download_to_drive(file_name)

    await update.message.reply_text("جاري تحويل الفيديو إلى MP3...")

    try:
        with open(file_name, 'rb') as f:
            response = requests.post(f"http://{SERVER_HOST}:{SERVER_PORT}/to_mp3", files={'file': f})

        if response.status_code == 200:
            mp3_path = os.path.join('static', f"converted_{os.path.splitext(file_name)[0]}.mp3")
            with open(mp3_path, 'wb') as f:
                f.write(response.content)

            await update.message.reply_audio(audio=open(mp3_path, 'rb'))
            os.remove(mp3_path)
        else:
            await update.message.reply_text(f"حدث خطأ أثناء تحويل الفيديو: {response.json().get('error')}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to server: {e}")
        await update.message.reply_text("لا يمكن الوصول إلى الخادم حاليًا.")
    finally:
        os.remove(file_name)

    await update.message.reply_text(
        'اختر أداة أخرى:',
        reply_markup=get_main_menu_keyboard()
    )
    return CHOOSING

# Text handler for QR code generation
async def qr_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if is_spam(update.effective_user.id): return WAITING_FOR_QR_TEXT
    text = update.message.text
    await update.message.reply_text("جاري إنشاء رمز QR...")

    try:
        response = requests.post(f"http://{SERVER_HOST}:{SERVER_PORT}/generate_qr", json={'text': text})

        if response.status_code == 200:
            qr_path = os.path.join('static', 'qr_code.png')
            with open(qr_path, 'wb') as f:
                f.write(response.content)

            await update.message.reply_photo(photo=open(qr_path, 'rb'))
            os.remove(qr_path)
        else:
            await update.message.reply_text(f"حدث خطأ أثناء إنشاء رمز QR: {response.json().get('error')}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to server: {e}")
        await update.message.reply_text("لا يمكن الوصول إلى الخادم حاليًا.")

    await update.message.reply_text(
        'اختر أداة أخرى:',
        reply_markup=get_main_menu_keyboard()
    )
    return CHOOSING

# File handler for zipping
async def zip_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if is_spam(update.effective_user.id): return WAITING_FOR_FILES_TO_ZIP
    if update.message.text and update.message.text.lower() == 'تم':
        await update.message.reply_text("جاري ضغط الملفات...")

        files_to_send = []
        for file_path in context.user_data['files_to_zip']:
            files_to_send.append(('files', (os.path.basename(file_path), open(file_path, 'rb'))))

        try:
            response = requests.post(f"http://{SERVER_HOST}:{SERVER_PORT}/zip_file", files=files_to_send)

            if response.status_code == 200:
                zip_path = os.path.join('static', 'archive.zip')
                with open(zip_path, 'wb') as f:
                    f.write(response.content)

                await update.message.reply_document(document=open(zip_path, 'rb'))
                os.remove(zip_path)
            else:
                await update.message.reply_text(f"حدث خطأ أثناء ضغط الملفات: {response.json().get('error')}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to server: {e}")
            await update.message.reply_text("لا يمكن الوصول إلى الخادم حاليًا.")
        finally:
            for file_path in context.user_data['files_to_zip']:
                os.remove(file_path)
            context.user_data['files_to_zip'] = []


        await update.message.reply_text(
            'اختر أداة أخرى:',
            reply_markup=get_main_menu_keyboard()
        )
        return CHOOSING

    else:
        document = await update.message.document.get_file()
        file_name = document.file_path.split('/')[-1]
        file_path = await document.download_to_drive(file_name)
        context.user_data['files_to_zip'].append(str(file_path))
        await update.message.reply_text("تم استلام الملف. أرسل المزيد من الملفات أو أرسل 'تم' للضغط.")
        return WAITING_FOR_FILES_TO_ZIP


# File handler for unzipping
async def unzip_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if is_spam(update.effective_user.id): return WAITING_FOR_ZIP_TO_UNZIP
    document = await update.message.document.get_file()
    file_name = document.file_path.split('/')[-1]
    file_path = await document.download_to_drive(file_name)

    await update.message.reply_text("جاري فك ضغط الملف...")

    try:
        with open(file_path, 'rb') as f:
            response = requests.post(f"http://{SERVER_HOST}:{SERVER_PORT}/unzip_file", files={'file': f})

        if response.status_code == 200:
            unzipped_path = os.path.join('static', 'unzipped_archive.zip')
            with open(unzipped_path, 'wb') as f:
                f.write(response.content)

            await update.message.reply_document(document=open(unzipped_path, 'rb'))
            os.remove(unzipped_path)
        else:
            await update.message.reply_text(f"حدث خطأ أثناء فك ضغط الملف: {response.json().get('error')}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to server: {e}")
        await update.message.reply_text("لا يمكن الوصول إلى الخادم حاليًا.")
    finally:
        os.remove(str(file_path))

    await update.message.reply_text(
        'اختر أداة أخرى:',
        reply_markup=get_main_menu_keyboard()
    )
    return CHOOSING

# Image handler for upscaling
async def upscale_image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if is_spam(update.effective_user.id): return WAITING_FOR_IMAGE_UPSCALE
    photo_file = await update.message.photo[-1].get_file()
    file_name = f"{photo_file.file_id}.jpg"
    await photo_file.download_to_drive(file_name)

    await update.message.reply_text("جاري تحسين الصورة...")

    try:
        with open(file_name, 'rb') as f:
            response = requests.post(f"http://{SERVER_HOST}:{SERVER_PORT}/upscale_4k", files={'file': f})

        if response.status_code == 200:
            processed_image_path = os.path.join('static', f"upscaled_{file_name}")
            with open(processed_image_path, 'wb') as f:
                f.write(response.content)

            await update.message.reply_photo(photo=open(processed_image_path, 'rb'))
            os.remove(processed_image_path)
        else:
            await update.message.reply_text(f"حدث خطأ أثناء تحسين الصورة: {response.json().get('error')}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to server: {e}")
        await update.message.reply_text("لا يمكن الوصول إلى الخادم حاليًا.")
    finally:
        os.remove(file_name)

    await update.message.reply_text(
        'اختر أداة أخرى:',
        reply_markup=get_main_menu_keyboard()
    )
    return CHOOSING

# Image handler for cropping
async def crop_image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if is_spam(update.effective_user.id): return WAITING_FOR_IMAGE_CROP
    photo_file = await update.message.photo[-1].get_file()
    file_name = f"{photo_file.file_id}.jpg"
    await photo_file.download_to_drive(file_name)

    await update.message.reply_text("جاري قص الصورة...")

    try:
        with open(file_name, 'rb') as f:
            response = requests.post(f"http://{SERVER_HOST}:{SERVER_PORT}/crop_image", files={'file': f})

        if response.status_code == 200:
            processed_image_path = os.path.join('static', f"cropped_{file_name}")
            with open(processed_image_path, 'wb') as f:
                f.write(response.content)

            await update.message.reply_photo(photo=open(processed_image_path, 'rb'))
            os.remove(processed_image_path)
        else:
            await update.message.reply_text(f"حدث خطأ أثناء قص الصورة: {response.json().get('error')}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error connecting to server: {e}")
        await update.message.reply_text("لا يمكن الوصول إلى الخادم حاليًا.")
    finally:
        os.remove(file_name)

    await update.message.reply_text(
        'اختر أداة أخرى:',
        reply_markup=get_main_menu_keyboard()
    )
    return CHOOSING

def get_tool_details_keyboard():
    keyboard = []
    for key, tool_info in TOOLS.items():
        keyboard.append([InlineKeyboardButton(tool_info["name"], callback_data=f"details_{key}")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='start')])
    return InlineKeyboardMarkup(keyboard)

async def tool_details_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if is_spam(update.effective_user.id): return WAITING_FOR_TOOL_DETAILS
    query = update.callback_query
    await query.answer()
    tool_key = query.data.split("_")[1]

    if tool_key == 'start':
        await query.edit_message_text(
            'أهلاً بك في بوت الأدوات! اختر أداة من القائمة:',
            reply_markup=get_main_menu_keyboard()
        )
        return CHOOSING

    if tool_key in TOOLS:
        await query.edit_message_text(TOOLS[tool_key]["desc"], reply_markup=get_tool_details_keyboard())

    return WAITING_FOR_TOOL_DETAILS

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING: [CallbackQueryHandler(button)],
            WAITING_FOR_IMAGE: [MessageHandler(filters.PHOTO, image_handler)],
            WAITING_FOR_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, url_handler)],
            WAITING_FOR_VIDEO_FILE: [MessageHandler(filters.VIDEO, video_file_handler)],
            WAITING_FOR_QR_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, qr_text_handler)],
            WAITING_FOR_FILES_TO_ZIP: [MessageHandler(filters.Document.ALL | (filters.TEXT & ~filters.COMMAND), zip_file_handler)],
            WAITING_FOR_ZIP_TO_UNZIP: [MessageHandler(filters.Document.ZIP, unzip_file_handler)],
            WAITING_FOR_IMAGE_UPSCALE: [MessageHandler(filters.PHOTO, upscale_image_handler)],
            WAITING_FOR_IMAGE_CROP: [MessageHandler(filters.PHOTO, crop_image_handler)],
            WAITING_FOR_TOOL_DETAILS: [CallbackQueryHandler(tool_details_handler)],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == "__main__":
    main()
