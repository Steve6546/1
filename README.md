# 📦 Telegram Tools Bot

An open-source Telegram bot that provides a collection of useful tools, accessible entirely through an intuitive inline button interface.

## ✨ Features

- **User-Friendly Interface**: A simple graphical interface based on buttons and categories.
- **Powerful Tools**: Leverages reliable and well-maintained open-source libraries.
- **Easily Extensible**: Add new tools by simply modifying the `tools.json` file.
- **Organized Structure**: Tools are grouped into categories for easy navigation.
- **Advanced Features**: Includes usage logging, favorite tools, spam protection, and update notifications.
- **Interactive Cropping**: A user-friendly interface for cropping images.

## 🛠️ Available Tools

### 🖼️ Image Tools
- **Remove Background**: Uses `rembg` to remove the background from images.
- **Upscale to 4K**: Employs `Real-ESRGAN` to enhance image resolution.
- **Crop Image**: An interactive cropping interface using `Pillow`.

### 🎬 Video Tools
- **Download Video**: Downloads videos from various platforms using `yt-dlp`.
- **Convert to MP3**: Converts video files to MP3 audio using `ffmpeg`.

### 📁 File Tools
- **Zip Files**: Compresses multiple files into a single `.zip` archive.
- **Unzip Files**: Extracts files from a `.zip` archive.

### 🧩 Other Tools
- **Generate QR Code**: Creates a QR code from text or a URL using `qrcode`.

---

## 🚀 Getting Started

Follow these instructions to get a local copy up and running.

### Prerequisites

- Python 3.8+
- `pip` for package management
- `git` for cloning the repository
- **(Optional but Recommended)** External dependencies for certain tools:
  - `ffmpeg`: Required for the "Convert to MP3" tool.
  - `realesrgan-ncnn-vulkan`: Required for the "Upscale to 4K" tool.

### Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/telegram-tools-bot.git
   cd telegram-tools-bot
   ```
   *(Note: Replace `your-username` with the actual repository owner's username if you are cloning from a fork).*

2. **Install Python packages:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the Bot Token:**
   - Open the `config.py` file.
   - Replace `"YOUR_TELEGRAM_BOT_TOKEN"` with your actual bot token obtained from [BotFather](https://t.me/botfather).

4. **Run the Backend Server:**
   The bot relies on a local Flask server to execute the tools. Run this in a terminal window:
   ```bash
   python server.py
   ```
   You should see output indicating the server is running on `http://0.0.0.0:8080/`.

5. **Run the Bot:**
   In a **separate** terminal window, run the bot itself:
   ```bash
   python bot.py
   ```
   Your bot should now be online and responsive on Telegram.

---

## 🏗️ Project Architecture

The bot operates with a client-server architecture:

- **`bot.py` (The Client)**: This is the main Telegram bot application, built with `python-telegram-bot`. It handles all user interactions, manages conversation states, and displays the UI (keyboards). When a user requests a tool, the bot sends the necessary data (files, URLs, etc.) to the backend server via HTTP requests.

- **`server.py` (The Server)**: This is a lightweight Flask server that acts as the backend. It exposes a simple API with endpoints for each tool (e.g., `/remove_bg`, `/download_video`). Its sole responsibility is to receive requests from the bot, execute the intensive processing tasks using the functions in the `tools/` directory, and return the resulting file or data.

This separation ensures that the user-facing bot remains responsive, while the heavy lifting is offloaded to a separate process.

---

## 🔧 How to Add a New Tool

Adding a new tool is designed to be simple and requires editing only two files.

1.  **Create the Tool Function:**
    -   In the appropriate file within the `tools/` directory (e.g., `tools/image.py`, `tools/other.py`), create a Python function that performs the desired action.
    -   This function should accept the Flask `app` instance and the necessary user input (e.g., a file, text) as arguments.
    -   It should return a Flask `send_from_directory` response with the resulting file or a `jsonify` error message.

2.  **Create the Server Endpoint:**
    -   Open `server.py`.
    -   Add a new Flask route (e.g., `@app.route('/my_new_tool', methods=['POST'])`).
    -   This route function should get the data from the request and call the tool function you created in the previous step.

3.  **Add the Tool to `tools.json`:**
    -   Open `tools.json`.
    -   Add a new entry for your tool under the desired category. Follow the existing structure:
        ```json
        "your_tool_key": {
          "name": "My New Awesome Tool",
          "desc": "A short description of what this tool does."
        }
        ```
    - The `"your_tool_key"` must be unique.

4.  **Update the Bot Handler:**
    -   Open `bot.py`.
    -   In the `select_tool` function, add a new `elif` condition for `"your_tool_key"`.
    -   This block should prompt the user for the required input and return the corresponding `WAITING_FOR_...` state.
    -   Create a new handler function (like `image_handler`, `url_handler`, etc.) to process the user's input, call the new server endpoint, and reply with the result.
    -   Finally, add your new handler and state to the `ConversationHandler` in the `main` function.

---

## 📝 License

This project is licensed under the MIT License. See the `LICENSE` file for details.
