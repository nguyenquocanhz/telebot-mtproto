# -*- coding: utf-8 -*-
# Config file for SellerBot

import os

# Telegram API Credentials (lấy từ https://my.telegram.org)
API_ID = int(os.getenv("TELEGRAM_API_ID", "1234567"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "YOUR_API_HASH_HERE")

# Telegram Bot Token (lấy từ @BotFather)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# Danh sách Telegram ID của Admin quản trị bot
ADMIN_IDS = [123456789]

# Ngân hàng nhận nạp tiền (VietQR)
BANK_NAME = "MBBank"
BANK_ACCOUNT_NO = "9999999999"
BANK_ACCOUNT_NAME = "NGUYEN QUOC ANH"
