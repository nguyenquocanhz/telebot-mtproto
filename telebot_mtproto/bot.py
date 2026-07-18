# -*- coding: utf-8 -*-
# Core Telebot MTProto implementation (bot.py)
# Một wrapper dựa trên Telethon giúp lập trình viên viết code với cú pháp đơn giản của pyTelegramBotAPI
# nhưng chạy trực tiếp trên giao thức MTProto (TCP) tốc độ cao và không giới hạn kích thước file gửi/nhận (hỗ trợ tới 2GB).

import asyncio
from typing import List, Callable, Any, Optional, Union
from telethon import TelegramClient, events
from telethon.tl.types import Message as TelethonMessage, User as TelethonUser

class ChatAdapter:
    """Giả lập đối tượng Chat của pyTelegramBotAPI"""
    def __init__(self, chat_id: int):
        self.id = chat_id

class UserAdapter:
    """Giả lập đối tượng User của pyTelegramBotAPI"""
    def __init__(self, user: TelethonUser):
        self.id = getattr(user, 'id', None)
        self.first_name = getattr(user, 'first_name', '')
        self.last_name = getattr(user, 'last_name', '')
        self.username = getattr(user, 'username', '')

class MessageAdapter:
    """Giả lập đối tượng Message của pyTelegramBotAPI từ đối tượng Event/Message của Telethon"""
    def __init__(self, event_message: TelethonMessage, sender: Optional[TelethonUser] = None):
        self.raw = event_message
        self.message_id = event_message.id
        self.text = event_message.message or ""
        self.caption = event_message.message or ""
        self.chat = ChatAdapter(event_message.chat_id)
        self.from_user = UserAdapter(sender) if sender else None
        
        # Xử lý tin nhắn reply
        self.reply_to_message = None
        if event_message.is_reply:
            # Lưu ID của tin nhắn được reply
            self.reply_to_message_id = event_message.reply_to.reply_to_msg_id

class MTProtoTeleBot:
    """Lớp điều khiển chính giả lập pyTelegramBotAPI chạy trên nền thức MTProto"""

    def __init__(self, api_id: int, api_hash: str, bot_token: Optional[str] = None, session_name: str = "telebot_mtproto"):
        """
        Khởi tạo MTProto Bot
        :param api_id: Telegram API ID (lấy từ my.telegram.org)
        :param api_hash: Telegram API HASH (lấy từ my.telegram.org)
        :param bot_token: Bot token (nếu chạy dưới quyền Bot @BotFather). Để trống nếu chạy chế độ Userbot.
        :param session_name: Tên tệp tin phiên làm việc session
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.bot_token = bot_token
        self.client = TelegramClient(session_name, api_id, api_hash)
        self.handlers = []

    def message_handler(self, commands: Optional[List[str]] = None, regexp: Optional[str] = None, func: Optional[Callable[[Any], bool]] = None):
        """
        Decorator đăng ký hàm xử lý tin nhắn tương tự pyTelegramBotAPI
        """
        def decorator(handler_func: Callable[[MessageAdapter], Any]):
            self.handlers.append({
                "func": handler_func,
                "commands": [c.lower() for c in commands] if commands else None,
                "regexp": regexp,
                "filter_func": func
            })
            return handler_func
        return decorator

    async def _handle_update(self, event):
        """Hàm xử lý và lọc sự kiện tin nhắn nội bộ"""
        msg = event.message
        if not msg:
            return

        # Lấy thông tin người gửi
        sender = await event.get_sender()
        adapted_msg = MessageAdapter(msg, sender)

        # Trích xuất command nếu có
        text_lower = adapted_msg.text.strip().lower()
        is_command = text_lower.startswith("/")
        command_name = text_lower.split()[0][1:] if is_command else ""

        for handler in self.handlers:
            # Lọc theo commands
            if handler["commands"] is not None:
                if not is_command or command_name not in handler["commands"]:
                    continue
            
            # Lọc theo regexp
            if handler["regexp"] is not None:
                import re
                if not re.search(handler["regexp"], adapted_msg.text):
                    continue
            
            # Lọc theo hàm filter_func tùy biến
            if handler["filter_func"] is not None:
                try:
                    if not handler["filter_func"](adapted_msg):
                        continue
                except Exception:
                    continue

            # Gọi handler (hỗ trợ cả hàm đồng bộ và không đồng bộ)
            if asyncio.iscoroutinefunction(handler["func"]):
                await handler["func"](adapted_msg)
            else:
                # Chạy hàm đồng bộ trong threadpool để tránh chặn vòng lặp sự kiện
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, handler["func"], adapted_msg)

    def start(self):
        """Khởi động client và đăng ký sự kiện"""
        # Đăng ký sự kiện nhận tin nhắn mới trong Telethon
        self.client.add_event_handler(self._handle_update, events.NewMessage(incoming=True))
        
        if self.bot_token:
            self.client.start(bot_token=self.bot_token)
        else:
            self.client.start()

    def run(self):
        """Bắt đầu chạy bot (blocking)"""
        self.start()
        print("Bot is running over MTProto...")
        self.client.run_until_disconnected()

    def send_message(self, chat_id: Union[int, str], text: str, reply_to_message_id: Optional[int] = None) -> TelethonMessage:
        """Gửi tin nhắn văn bản"""
        loop = asyncio.get_event_loop()
        coro = self.client.send_message(chat_id, text, reply_to=reply_to_message_id)
        if loop.is_running():
            return asyncio.ensure_future(coro)
        return loop.run_until_complete(coro)

    def reply_to(self, message: MessageAdapter, text: str) -> TelethonMessage:
        """Trả lời trực tiếp một tin nhắn"""
        return self.send_message(message.chat.id, text, reply_to_message_id=message.message_id)

    def send_document(self, chat_id: Union[int, str], file_path: str, caption: Optional[str] = None) -> TelethonMessage:
        """Gửi tài liệu/tệp tin (Hỗ trợ file cực lớn lên tới 2GB)"""
        loop = asyncio.get_event_loop()
        coro = self.client.send_file(chat_id, file_path, caption=caption, force_document=True)
        if loop.is_running():
            return asyncio.ensure_future(coro)
        return loop.run_until_complete(coro)

    def send_photo(self, chat_id: Union[int, str], file_path: str, caption: Optional[str] = None) -> TelethonMessage:
        """Gửi ảnh"""
        loop = asyncio.get_event_loop()
        coro = self.client.send_file(chat_id, file_path, caption=caption)
        if loop.is_running():
            return asyncio.ensure_future(coro)
        return loop.run_until_complete(coro)

    def download_file(self, message: MessageAdapter, dest_path: str) -> str:
        """Tải tệp đính kèm trong tin nhắn về máy (Không giới hạn 20MB của HTTP Bot API)"""
        loop = asyncio.get_event_loop()
        coro = self.client.download_media(message.raw, file=dest_path)
        if loop.is_running():
            return asyncio.ensure_future(coro)
        return loop.run_until_complete(coro)
