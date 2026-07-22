# Telebot MTProto 🚀

[![PyPI version](https://img.shields.io/pypi/v/telebot-mtproto.svg)](https://pypi.org/project/telebot-mtproto/)
[![Python Version](https://img.shields.io/pypi/pyversions/telebot-mtproto.svg)](https://pypi.org/project/telebot-mtproto/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A lightweight, powerful Python wrapper that brings the simple and familiar decorator-based syntax of **`pyTelegramBotAPI` (`telebot`)** to the high-performance **MTProto** protocol (powered by **Telethon** under the hood).

---

## ⚡ Why Telebot MTProto?

When building Telegram bots with standard HTTP-based Bot API libraries (`pyTelegramBotAPI` / `telebot`), you hit severe Telegram HTTP server limits:
- ❌ Cannot download files larger than **20MB**.
- ❌ Cannot upload files larger than **50MB**.
- ❌ HTTP REST polling/webhooks introduce unnecessary request overhead.

**Telebot MTProto solves all of these limitations!** By running directly over Telegram's binary **MTProto protocol (TCP)**:
- ✅ **Send & Download Large Files**: Up to **2GB** (or **4GB** with Telegram Premium).
- ✅ **Real-time Progress Callbacks**: Track exact upload/download percentage.
- ✅ **Dual Account Mode**: Run as a **Bot** (using Bot Token) or as a **Userbot** (using phone login session).
- ✅ **Full Keyboard Support**: Build `InlineKeyboardMarkup` and `ReplyKeyboardMarkup` effortlessly.
- ✅ **Direct Proxy Integration**: Built-in support for SOCKS5, HTTP, and MTProto Proxies.
- ✅ **Zero Learning Curve**: Use your existing `pyTelegramBotAPI` knowledge and syntax!

---

## 📦 Installation

### Option 1: Via PyPI (Recommended)
```bash
pip install telebot-mtproto
```

### Option 2: Directly from GitHub
```bash
pip install git+https://github.com/nguyenquocanhz/telebot-mtproto.git
```

---

## 🚀 Quick Start Examples

### 1. Basic Bot (with Bot Token)

Get your `api_id` and `api_hash` from [https://my.telegram.org](https://my.telegram.org):

```python
from telebot_mtproto import MTProtoTeleBot

bot = MTProtoTeleBot(
    api_id=1234567,
    api_hash="YOUR_API_HASH",
    bot_token="YOUR_BOT_TOKEN"
)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Hello! I am running on MTProto protocol.")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"You said: {message.text}")

# Start polling
bot.run()
```

---

### 2. Interactive Inline Keyboards & Callback Queries

```python
from telebot_mtproto import MTProtoTeleBot
from telebot_mtproto.types import InlineKeyboardMarkup, InlineKeyboardButton

bot = MTProtoTeleBot(api_id=1234567, api_hash="YOUR_API_HASH", bot_token="YOUR_BOT_TOKEN")

@bot.message_handler(commands=['menu'])
def show_menu(message):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("GitHub Repo", url="https://github.com/nguyenquocanhz/telebot-mtproto"),
        InlineKeyboardButton("Click Me", callback_data="btn_click")
    )
    bot.send_message(message.chat.id, "Please select an option:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    if call.data == "btn_click":
        bot.answer_callback_query(call.id, text="You clicked the button!", show_alert=True)

bot.run()
```

---

### 3. Send & Download Large Files (> 20MB / 50MB) with Progress Bar

```python
from telebot_mtproto import MTProtoTeleBot

bot = MTProtoTeleBot(api_id=1234567, api_hash="YOUR_API_HASH", bot_token="YOUR_BOT_TOKEN")

def progress(current, total):
    print(f"Transferred: {current}/{total} bytes ({current/total*100:.1f}%)")

# Upload up to 2GB / 4GB file
@bot.message_handler(commands=['send_big'])
def send_large_file(message):
    bot.reply_to(message, "Uploading large video file...")
    bot.send_video(message.chat.id, "./media/huge_video.mp4", progress_callback=progress)

# Download large file directly via MTProto
@bot.message_handler(content_types=['document', 'video', 'photo'])
def download_large_file(message):
    bot.reply_to(message, "Downloading media file...")
    dest = f"./downloads/{message.message_id}.file"
    bot.download_file(message, dest, progress_callback=progress)
    bot.reply_to(message, f"File saved to {dest}")

bot.run()
```

---

### 4. Userbot Mode (Phone Login)

If you omit `bot_token`, it will run as a **Userbot** acting on behalf of a personal Telegram account:

```python
from telebot_mtproto import MTProtoTeleBot

bot = MTProtoTeleBot(
    api_id=1234567,
    api_hash="YOUR_API_HASH",
    session_name="my_userbot_session"
)

@bot.message_handler(commands=['ping'])
def ping(message):
    bot.reply_to(message, "Pong from Userbot!")

bot.run()
```

---

### 5. Proxy Support (SOCKS5 / HTTP / MTProto)

```python
from telebot_mtproto import MTProtoTeleBot

bot = MTProtoTeleBot(
    api_id=1234567,
    api_hash="YOUR_API_HASH",
    bot_token="YOUR_BOT_TOKEN",
    proxy=("socks5", "127.0.0.1", 1080)
)
```

---

## 🛠️ Supported Content Types

Filter messages effortlessly using `content_types`:
- `'text'`
- `'photo'`
- `'video'`
- `'document'`
- `'audio'`
- `'voice'`
- `'sticker'`
- `'location'`
- `'contact'`

```python
@bot.message_handler(content_types=['photo', 'video'])
def handle_media_messages(message):
    print(f"Received media of type: {message.content_type}")
```

---

## 📋 API Reference

| Method / Decorator | Description |
| :--- | :--- |
| `@bot.message_handler(...)` | Filter and handle incoming messages (`content_types`, `commands`, `regexp`, `func`) |
| `@bot.callback_query_handler(...)` | Handle inline keyboard button clicks |
| `bot.send_message(chat_id, text, ...)` | Send text messages |
| `bot.reply_to(message, text, ...)` | Reply directly to a message |
| `bot.send_document(chat_id, file_path, ...)` | Send documents up to 2GB/4GB |
| `bot.send_photo(chat_id, file_path, ...)` | Send photo files |
| `bot.send_video(chat_id, file_path, ...)` | Send video files |
| `bot.send_audio(chat_id, file_path, ...)` | Send audio files |
| `bot.send_voice(chat_id, file_path, ...)` | Send voice messages |
| `bot.send_sticker(chat_id, file_path)` | Send stickers |
| `bot.send_location(chat_id, lat, lon)` | Send geographic location |
| `bot.download_file(message, dest_path, ...)` | Download attached media |
| `bot.answer_callback_query(call_id, ...)` | Respond to inline button clicks |
| `bot.edit_message_text(chat_id, msg_id, text)` | Edit an existing message |
| `bot.delete_message(chat_id, msg_id)` | Delete a message |
| `bot.forward_message(chat_id, from_chat_id, msg_id)` | Forward a message |

---

## 📄 License

Distributed under the MIT License. See [LICENSE](file:///d:/SellBot/LICENSE) for details.
