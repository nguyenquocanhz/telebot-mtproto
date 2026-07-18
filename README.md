# Telebot MTProto for Python

A lightweight wrapper that brings the simple and familiar decorator-based syntax of `pyTelegramBotAPI` (Telebot) to the high-performance **MTProto** protocol (using Telethon under the hood).

## Why Telebot MTProto?

When building Telegram bots with `pyTelegramBotAPI` (`telebot`), you are limited by the HTTP-based Bot API:
- Cannot download files larger than **20MB**.
- Cannot upload files larger than **50MB**.
- HTTP overhead slows down responses.

**Telebot MTProto** solves this! By running directly over MTProto (TCP):
- **Send & Download files up to 2GB** (or 4GB with Telegram Premium).
- **Run as a Bot** (using bot token) or as a **Userbot** (using phone login session).
- Enjoy direct TCP speed with zero-change friendly Telebot syntax.

## Installation

Install using pip:

```bash
pip install telebot-mtproto
```

## Quick Start

### 1. Run as a Bot Account (with Token)

```python
from telebot_mtproto import MTProtoTeleBot

# Get api_id and api_hash from https://my.telegram.org
bot = MTProtoTeleBot(
    api_id=123456,
    api_hash="your_api_hash",
    bot_token="your_bot_token_from_botfather"
)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Hello! I am running on MTProto protocol.")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"You said: {message.text}")

# Start the bot
bot.run()
```

### 2. Run as a Userbot Account (with Phone Login)

If you don't provide a `bot_token`, it will act as a Userbot. During the first run, it will prompt you in the terminal to enter your phone number and the OTP code sent by Telegram.

```python
from telebot_mtproto import MTProtoTeleBot

bot = MTProtoTeleBot(
    api_id=123456,
    api_hash="your_api_hash",
    session_name="my_userbot_session"
)

@bot.message_handler(commands=['ping'])
def ping(message):
    bot.reply_to(message, "Pong from userbot!")

bot.run()
```

### 3. Send and Download Large Files (> 20MB)

```python
@bot.message_handler(commands=['download'])
def get_large_file(message):
    if message.reply_to_message:
        bot.reply_to(message, "Downloading large file... (up to 2GB supported)")
        
        # Download file directly over MTProto TCP
        dest = "./downloads/large_file.zip"
        bot.download_file(message.reply_to_message, dest)
        
        bot.reply_to(message, f"File saved to {dest}")
```

## License

MIT License.
