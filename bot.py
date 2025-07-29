# -*- coding: utf-8 -*-
"""
Telegram Bot for Various Tools

This bot provides a user-friendly interface for a variety of tools,
including image manipulation, video downloading, and file management.
"""

import logging
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, ConversationHandler
from config import BOT_TOKEN, SERVER_HOST, SERVER_PORT
import os
import json
import time
from datetime import datetime
from PIL import Image

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Data Loading ---
try:
    with open('tools.json', 'r', encoding='utf-8') as f:
        TOOLS = json.load(f)
    with open('user_logs.json', 'r', encoding='utf-8') as f:
        USER_LOGS = json.load(f)
    with open('user_favorites.json', 'r', encoding='utf-8') as f:
        USER_FAVORITES = json.load(f)
    with open('last_tools.json', 'r', encoding='utf-8') as f:
        LAST_TOOLS = json.load(f)
except FileNotFoundError as e:
    logger.error(f"Error loading data file: {e}. Please ensure all .json files exist.")
    exit()


# --- Conversation States ---
(
    CHOOSING_CATEGORY, CHOOSING_TOOL, WAITING_FOR_IMAGE, WAITING_FOR_URL,
    WAITING_FOR_VIDEO_FILE, WAITING_FOR_QR_TEXT, WAITING_FOR_FILES_TO_ZIP,
    WAITING_FOR_ZIP_TO_UNZIP, WAITING_FOR_IMAGE_UPSCALE, WAITING_FOR_IMAGE_CROP,
    WAITING_FOR_TOOL_DETAILS, MANAGING_FAVORITES, WAITING_FOR_CROP_DIMS,
    INTERACTIVE_CROP
) = range(14)


# --- Helper Functions ---

user_timestamps = {}
SPAM_LIMIT = 3  # seconds

def is_spam(user_id: int) -> bool:
    """
    Checks if a user is spamming the bot.
    Returns True if the user is spamming, False otherwise.
    """
    current_time = time.time()
    if user_id in user_timestamps and current_time - user_timestamps.get(user_id, 0) < SPAM_LIMIT:
        return True
    user_timestamps[user_id] = current_time
    return False

def log_tool_usage(user_id: int, tool_key: str) -> None:
    """Logs the usage of a tool by a user."""
    user_id_str = str(user_id)
    if user_id_str not in USER_LOGS:
        USER_LOGS[user_id_str] = []

    log_entry = {
        "tool": tool_key,
        "timestamp": datetime.now().isoformat()
    }
    USER_LOGS[user_id_str].append(log_entry)

    with open('user_logs.json', 'w', encoding='utf-8') as f:
        json.dump(USER_LOGS, f, indent=4)


# --- Keyboard Generators ---

def get_category_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Generates the main menu keyboard with tool categories."""
    keyboard = []
    user_id_str = str(user_id)
    if user_id_str in USER_FAVORITES and USER_FAVORITES[user_id_str]:
        keyboard.append([InlineKeyboardButton("⭐ المفضلة", callback_data='favorites')])

    for category_key, category_data in TOOLS.items():
        keyboard.append([InlineKeyboardButton(category_data["name"], callback_data=f"category_{category_key}")])

    keyboard.append([InlineKeyboardButton("⚙️ إدارة المفضلة", callback_data='manage_favorites')])
    keyboard.append([InlineKeyboardButton("ℹ️ تفاصيل الأداة", callback_data='tool_details'), InlineKeyboardButton("🤖 حول البوت", callback_data='about')])
    keyboard.append([InlineKeyboardButton("🔔 تحديثات المشروع", callback_data='updates')])
    keyboard.append([InlineKeyboardButton("🗑️ مسح المحادثة", callback_data='clear_chat')])
    return InlineKeyboardMarkup(keyboard)


def get_favorites_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Generates the keyboard for the user's favorite tools."""
    keyboard = []
    user_id_str = str(user_id)
    if user_id_str in USER_FAVORITES:
        for tool_key in USER_FAVORITES[user_id_str]:
            for category_data in TOOLS.values():
                if tool_key in category_data["tools"]:
                    keyboard.append([InlineKeyboardButton(category_data["tools"][tool_key]["name"], callback_data=f"tool_{tool_key}")])
                    break
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='start')])
    return InlineKeyboardMarkup(keyboard)


def get_favorites_management_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Generates the keyboard for managing favorite tools."""
    keyboard = []
    user_id_str = str(user_id)
    for category_key, category_data in TOOLS.items():
        for tool_key, tool_info in category_data["tools"].items():
            is_favorite = user_id_str in USER_FAVORITES and tool_key in USER_FAVORITES[user_id_str]
            button_text = f"{tool_info['name']} {'⭐' if is_favorite else '☆'}"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=f"fav_{tool_key}")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='start')])
    return InlineKeyboardMarkup(keyboard)

def get_tool_details_keyboard() -> InlineKeyboardMarkup:
    """Generates the keyboard for viewing tool details."""
    keyboard = []
    for category_key, category_data in TOOLS.items():
        for tool_key, tool_info in category_data["tools"].items():
            keyboard.append([InlineKeyboardButton(tool_info["name"], callback_data=f"details_{tool_key}")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='start')])
    return InlineKeyboardMarkup(keyboard)

def get_tool_keyboard(category_key):
    tools = TOOLS[category_key]["tools"]
    keyboard = []
    for tool_key, tool_data in tools.items():
        keyboard.append([InlineKeyboardButton(tool_data["name"], callback_data=f"tool_{tool_key}")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='start')])
    return InlineKeyboardMarkup(keyboard)

def get_crop_keyboard(left, top, right, bottom):
    """Generates the keyboard for interactive cropping."""
    step = 10
    keyboard = [
        [InlineKeyboardButton("⬆️", callback_data=f"crop_up_{step}")],
        [
            InlineKeyboardButton("⬅️", callback_data=f"crop_left_{step}"),
            InlineKeyboardButton("➡️", callback_data=f"crop_right_{step}")
        ],
        [InlineKeyboardButton("⬇️", callback_data=f"crop_down_{step}")],
        [
            InlineKeyboardButton("➕", callback_data=f"crop_zoom_in_{step}"),
            InlineKeyboardButton("➖", callback_data=f"crop_zoom_out_{step}")
        ],
        [InlineKeyboardButton("✅ قص", callback_data="crop_done")],
        [InlineKeyboardButton("🔙 رجوع", callback_data='start')]
    ]
    return InlineKeyboardMarkup(keyboard)


# --- Command and Callback Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Starts the conversation and displays the main menu.
    Can be triggered by /start command or a callback query.
    """
    user_id = update.effective_user.id
    if is_spam(user_id):
        return CHOOSING_CATEGORY

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            'أهلاً بك في بوت الأدوات! اختر فئة من القائمة:',
            reply_markup=get_category_keyboard(user_id)
        )
    else:
        await update.message.reply_text(
            'أهلاً بك في بوت الأدوات! اختر فئة من القائمة:',
            reply_markup=get_category_keyboard(user_id)
        )
    return CHOOSING_CATEGORY


async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles category selection from the main menu."""
    user_id = update.effective_user.id
    if is_spam(user_id):
        return CHOOSING_CATEGORY

    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'favorites':
        await query.edit_message_text("أدواتك المفضلة:", reply_markup=get_favorites_keyboard(user_id))
        return CHOOSING_TOOL

    if data == 'manage_favorites':
        await query.edit_message_text("اختر الأدوات لإضافتها أو إزالتها من المفضلة:", reply_markup=get_favorites_management_keyboard(user_id))
        return MANAGING_FAVORITES

    if data == 'about':
        await query.edit_message_text(
            "هذا البوت هو مشروع مفتوح المصدر يهدف إلى توفير أدوات مفيدة لمستخدمي تيليجرام.\n\n"
            "يمكنك المساهمة في المشروع على GitHub: [رابط المشروع](https://github.com/your-username/telegram-tools-bot)",
            parse_mode='Markdown',
            reply_markup=get_category_keyboard(user_id)
        )
        return CHOOSING_CATEGORY

    if data == 'clear_chat':
        await query.edit_message_text("هذه الميزة قيد التطوير.", reply_markup=get_category_keyboard(user_id))
        return CHOOSING_CATEGORY

    if data == 'tool_details':
        await query.edit_message_text("اختر أداة لعرض تفاصيلها:", reply_markup=get_tool_details_keyboard())
        return WAITING_FOR_TOOL_DETAILS

    if data == 'updates':
        new_tools = []
        for category_key, category_data in TOOLS.items():
            if category_key not in LAST_TOOLS or not LAST_TOOLS[category_key]:
                new_tools.extend(category_data["tools"].values())
            else:
                for tool_key, tool_info in category_data["tools"].items():
                    if tool_key not in LAST_TOOLS[category_key]["tools"]:
                        new_tools.append(tool_info)

        if new_tools:
            message = "تمت إضافة الأدوات الجديدة التالية:\n\n"
            for tool in new_tools:
                message += f"- {tool['name']}: {tool['desc']}\n"

            # Update last_tools.json
            with open('last_tools.json', 'w', encoding='utf-8') as f:
                json.dump(TOOLS, f, indent=4)
        else:
            message = "لا توجد تحديثات جديدة في الوقت الحالي."

        await query.edit_message_text(message, reply_markup=get_category_keyboard(user_id))
        return CHOOSING_CATEGORY

    category_key = data.split("_")[1]
    context.user_data['selected_category'] = category_key

    await query.edit_message_text(
        text=f"اختر أداة من فئة: {TOOLS[category_key]['name']}",
        reply_markup=get_tool_keyboard(category_key)
    )
    return CHOOSING_TOOL


async def select_tool(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handles tool selection and prompts the user for input."""
    user_id = update.effective_user.id
    if is_spam(user_id):
        return CHOOSING_TOOL

    query = update.callback_query
    await query.answer()
    tool = query.data.split("_")[1]

    log_tool_usage(user_id, tool)

    if tool == 'start':
        await query.edit_message_text(
            'أهلاً بك في بوت الأدوات! اختر فئة من القائمة:',
            reply_markup=get_category_keyboard(user_id)
        )
        return CHOOSING_CATEGORY

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
        await query.edit_message_text(text="أرسل لي الصورة التي تريد قصها.")
        return WAITING_FOR_IMAGE_CROP
    else:
        await query.edit_message_text(text=f"تم اختيار أداة: {tool}. هذه الميزة قيد التطوير.", reply_markup=get_tool_keyboard(context.user_data['selected_category']))
        return CHOOSING_TOOL

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
        reply_markup=get_category_keyboard(update.effective_user.id)
    )
    return CHOOSING_CATEGORY


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
        reply_markup=get_category_keyboard(update.effective_user.id)
    )
    return CHOOSING_CATEGORY

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
        reply_markup=get_category_keyboard(update.effective_user.id)
    )
    return CHOOSING_CATEGORY

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
        reply_markup=get_category_keyboard(update.effective_user.id)
    )
    return CHOOSING_CATEGORY

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
            reply_markup=get_category_keyboard(update.effective_user.id)
        )
        return CHOOSING_CATEGORY

    else:
        document = await update.message.document.get_file()
        file_name = document.file_path.split('/')[-1]
        file_path = await document.download_to_drive(file_name)
        context.user_data['files_to_zip'].append(str(file_path))
        await update.message.reply_text("تم استلام الملف. أرسل المزيد من الملفات أو أرسل 'تم' للضغط.")
        return WAITING_FOR_FILES_TO_ZIP


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
        reply_markup=get_category_keyboard(update.effective_user.id)
    )
    return CHOOSING_CATEGORY

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
        reply_markup=get_category_keyboard(update.effective_user.id)
    )
    return CHOOSING_CATEGORY

async def crop_image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo_file = await update.message.photo[-1].get_file()
    file_name = f"{photo_file.file_id}.jpg"
    file_path = await photo_file.download_to_drive(file_name)

    img = Image.open(file_path)
    width, height = img.size

    # Initial crop dimensions (center)
    left = width / 4
    top = height / 4
    right = 3 * width / 4
    bottom = 3 * height / 4

    context.user_data['crop_file_path'] = str(file_path)
    context.user_data['crop_dims'] = {'left': left, 'top': top, 'right': right, 'bottom': bottom}

    await update.message.reply_photo(
        photo=open(file_path, 'rb'),
        caption="استخدم الأزرار لضبط القص.",
        reply_markup=get_crop_keyboard(left, top, right, bottom)
    )
    return INTERACTIVE_CROP

async def interactive_crop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    data = query.data
    step = int(data.split("_")[-1]) if "_" in data else 0
    dims = context.user_data['crop_dims']

    if "left" in data: dims['left'] -= step; dims['right'] -= step
    if "right" in data: dims['left'] += step; dims['right'] += step
    if "up" in data: dims['top'] -= step; dims['bottom'] -= step
    if "down" in data: dims['top'] += step; dims['bottom'] += step
    if "zoom_in" in data:
        dims['left'] += step; dims['top'] += step
        dims['right'] -= step; dims['bottom'] -= step
    if "zoom_out" in data:
        dims['left'] -= step; dims['top'] -= step
        dims['right'] += step; dims['bottom'] += step

    if "done" in data:
        file_path = context.user_data['crop_file_path']
        file_name = os.path.basename(file_path)

        await query.edit_message_caption(caption="جاري قص الصورة...")

        try:
            with open(file_path, 'rb') as f:
                data = dims
                response = requests.post(f"http://{SERVER_HOST}:{SERVER_PORT}/crop_image", files={'file': f}, data=data)

            if response.status_code == 200:
                processed_image_path = os.path.join('static', f"cropped_{file_name}")
                with open(processed_image_path, 'wb') as f:
                    f.write(response.content)

                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
                await context.bot.send_photo(chat_id=query.message.chat_id, photo=open(processed_image_path, 'rb'))
                os.remove(processed_image_path)
            else:
                await query.message.reply_text(f"حدث خطأ أثناء قص الصورة: {response.json().get('error')}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error connecting to server: {e}")
            await query.message.reply_text("لا يمكن الوصول إلى الخادم حاليًا.")
        finally:
            os.remove(file_path)
            del context.user_data['crop_file_path']
            del context.user_data['crop_dims']

        await query.message.reply_text(
            'اختر أداة أخرى:',
            reply_markup=get_category_keyboard(update.effective_user.id)
        )
        return CHOOSING_CATEGORY

    # Update the preview
    file_path = context.user_data['crop_file_path']
    try:
        data = dims
        response = requests.post(f"http://{SERVER_HOST}:{SERVER_PORT}/preview_crop", data={'filepath': file_path, **data})
        if response.status_code == 200:
            preview_path = os.path.join('static', f"preview_{os.path.basename(file_path)}")
            with open(preview_path, 'wb') as f:
                f.write(response.content)

            await query.edit_message_media(
                media=InputMediaPhoto(media=open(preview_path, 'rb')),
                reply_markup=get_crop_keyboard(**dims)
            )
            os.remove(preview_path)
    except Exception as e:
        logger.error(f"Error updating crop preview: {e}")

    return INTERACTIVE_CROP


async def tool_details_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if is_spam(update.effective_user.id): return WAITING_FOR_TOOL_DETAILS
    query = update.callback_query
    await query.answer()
    tool_key = query.data.split("_")[1]

    if tool_key == 'start':
        await query.edit_message_text(
            'أهلاً بك في بوت الأدوات! اختر فئة من القائمة:',
            reply_markup=get_category_keyboard(update.effective_user.id)
        )
        return CHOOSING_CATEGORY

    for category_data in TOOLS.values():
        if tool_key in category_data["tools"]:
            await query.edit_message_text(category_data["tools"][tool_key]["desc"], reply_markup=get_tool_details_keyboard())
            break

    return WAITING_FOR_TOOL_DETAILS

async def manage_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)

    if query.data == 'manage_favorites':
        await query.edit_message_text("اختر الأدوات لإضافتها أو إزالتها من المفضلة:", reply_markup=get_favorites_management_keyboard(user_id))
        return MANAGING_FAVORITES

    tool_key = query.data.split("_")[1]

    if user_id not in USER_FAVORITES:
        USER_FAVORITES[user_id] = []

    if tool_key in USER_FAVORITES[user_id]:
        USER_FAVORITES[user_id].remove(tool_key)
    else:
        USER_FAVORITES[user_id].append(tool_key)

    with open('user_favorites.json', 'w', encoding='utf-8') as f:
        json.dump(USER_FAVORITES, f, indent=4)

    await query.edit_message_text("تم تحديث المفضلة.", reply_markup=get_favorites_management_keyboard(user_id))
    return MANAGING_FAVORITES

async def crop_dims_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    dims_text = update.message.text
    try:
        left, top, right, bottom = [int(d.strip()) for d in dims_text.split(',')]
    except ValueError:
        await update.message.reply_text("صيغة غير صالحة. الرجاء إرسال الأبعاد بالصيغة التالية: left,top,right,bottom")
        return WAITING_FOR_CROP_DIMS

    file_path = context.user_data['crop_file_path']
    file_name = os.path.basename(file_path)

    await update.message.reply_text("جاري قص الصورة...")

    try:
        with open(file_path, 'rb') as f:
            data = {'left': left, 'top': top, 'right': right, 'bottom': bottom}
            response = requests.post(f"http://{SERVER_HOST}:{SERVER_PORT}/crop_image", files={'file': f}, data=data)

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
        os.remove(file_path)
        del context.user_data['crop_file_path']

    await update.message.reply_text(
        'اختر أداة أخرى:',
        reply_markup=get_category_keyboard(update.effective_user.id)
    )
    return CHOOSING_CATEGORY


def main() -> None:
    """Initializes and runs the bot."""
    print("Initializing application...")
    application = Application.builder().token(BOT_TOKEN).build()
    print("Application initialized.")

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CallbackQueryHandler(start, pattern='^start$')],
        states={
            CHOOSING_CATEGORY: [CallbackQueryHandler(select_category)],
            CHOOSING_TOOL: [CallbackQueryHandler(select_tool, pattern="^tool_")],
            WAITING_FOR_IMAGE: [MessageHandler(filters.PHOTO, image_handler)],
            WAITING_FOR_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, url_handler)],
            WAITING_FOR_VIDEO_FILE: [MessageHandler(filters.VIDEO, video_file_handler)],
            WAITING_FOR_QR_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, qr_text_handler)],
            WAITING_FOR_FILES_TO_ZIP: [MessageHandler(filters.Document.ALL | (filters.TEXT & ~filters.COMMAND), zip_file_handler)],
            WAITING_FOR_ZIP_TO_UNZIP: [MessageHandler(filters.Document.ZIP, unzip_file_handler)],
            WAITING_FOR_IMAGE_UPSCALE: [MessageHandler(filters.PHOTO, upscale_image_handler)],
            WAITING_FOR_IMAGE_CROP: [MessageHandler(filters.PHOTO, crop_image_handler)],
            WAITING_FOR_CROP_DIMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, crop_dims_handler)],
            INTERACTIVE_CROP: [CallbackQueryHandler(interactive_crop_handler)],
            WAITING_FOR_TOOL_DETAILS: [CallbackQueryHandler(tool_details_handler)],
            MANAGING_FAVORITES: [CallbackQueryHandler(manage_favorites)],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    print("Conversation handler created.")

    application.add_handler(conv_handler)
    print("Conversation handler added.")

    print("Starting polling...")
    application.run_polling()
    print("Polling stopped.")


if __name__ == "__main__":
    print("Starting bot...")
    main()
    print("Bot stopped.")
