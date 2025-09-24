# -*- coding: utf-8 -*-
"""
Configuration settings for the Telegram Tools Bot.

This file contains the essential configuration variables needed to run both
the Telegram bot (`bot.py`) and the backend server (`server.py`).
"""

# --- Telegram Bot Configuration ---

# Your unique Telegram bot token obtained from BotFather.
# Replace "YOUR_TELEGRAM_BOT_TOKEN" with your actual token.
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"


# --- Backend Server Configuration ---

# The host address for the backend server.
# "0.0.0.0" makes the server accessible on the local network.
SERVER_HOST = "0.0.0.0"

# The port for the backend server.
# Ensure this port is not in use by another application.
SERVER_PORT = 8080
