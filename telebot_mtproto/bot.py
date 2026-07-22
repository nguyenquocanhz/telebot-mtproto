# -*- coding: utf-8 -*-
# Core Telebot MTProto implementation (bot.py)
# Một wrapper dựa trên Telethon giúp lập trình viên viết code với cú pháp đơn giản của pyTelegramBotAPI
# nhưng chạy trực tiếp trên giao thức MTProto (TCP) tốc độ cao và không giới hạn kích thước file gửi/nhận (hỗ trợ tới 2GB).

import asyncio
import re
from typing import List, Callable, Any, Optional, Union
from telethon import TelegramClient, events
from telethon.tl.types import (
    Message as TelethonMessage,
    User as TelethonUser,
    MessageMediaPhoto,
    MessageMediaDocument,
    MessageMediaGeo,
    MessageMediaContact,
)

class ChatAdapter:
    """Giả lập đối tượng Chat của pyTelegramBotAPI"""
    def __init__(self, chat_id: int):
        self.id = chat_id

class UserAdapter:
    """Giả lập đối tượng User của pyTelegramBotAPI"""
    def __init__(self, user: Optional[TelethonUser]):
        if user:
            self.id = getattr(user, 'id', None)
            self.first_name = getattr(user, 'first_name', '')
            self.last_name = getattr(user, 'last_name', '')
            self.username = getattr(user, 'username', '')
        else:
            self.id = None
            self.first_name = ''
            self.last_name = ''
            self.username = ''

class MessageAdapter:
    """Giả lập đối tượng Message của pyTelegramBotAPI từ đối tượng Event/Message của Telethon"""
    def __init__(self, event_message: TelethonMessage, sender: Optional[TelethonUser] = None):
        self.raw = event_message
        self.message_id = event_message.id
        self.text = event_message.message or ""
        self.caption = event_message.message or ""
        self.chat = ChatAdapter(event_message.chat_id)
        self.from_user = UserAdapter(sender)

        # Xác định content_type và media đính kèm
        self.content_type = "text"
        self.photo = None
        self.document = None
        self.video = None
        self.audio = None
        self.voice = None
        self.sticker = None
        self.location = None
        self.contact = None

        if event_message.media:
            if isinstance(event_message.media, MessageMediaPhoto):
                self.content_type = "photo"
                self.photo = event_message.media
            elif isinstance(event_message.media, MessageMediaDocument):
                doc = event_message.document
                if doc:
                    mime = getattr(doc, 'mime_type', '') or ''
                    if mime.startswith('video/'):
                        self.content_type = "video"
                        self.video = doc
                    elif mime.startswith('audio/'):
                        self.content_type = "audio"
                        self.audio = doc
                    elif 'ogg' in mime or getattr(event_message, 'voice', None):
                        self.content_type = "voice"
                        self.voice = doc
                    elif mime == 'application/x-bad-sticker' or getattr(event_message, 'sticker', None):
                        self.content_type = "sticker"
                        self.sticker = doc
                    else:
                        self.content_type = "document"
                        self.document = doc
            elif isinstance(event_message.media, MessageMediaGeo):
                self.content_type = "location"
                self.location = event_message.media
            elif isinstance(event_message.media, MessageMediaContact):
                self.content_type = "contact"
                self.contact = event_message.media

        # Xử lý tin nhắn reply
        self.reply_to_message = None
        self.reply_to_message_id = None
        if event_message.is_reply and getattr(event_message, 'reply_to', None):
            self.reply_to_message_id = getattr(event_message.reply_to, 'reply_to_msg_id', None)

class CallbackQueryAdapter:
    """Giả lập đối tượng CallbackQuery của pyTelegramBotAPI cho nút bấm Inline"""
    def __init__(self, event):
        self.raw = event
        self.id = str(event.query.id) if getattr(event, 'query', None) else ""
        self.data = event.data.decode('utf-8') if isinstance(event.data, bytes) else (event.data or "")
        self.from_user = UserAdapter(getattr(event, 'sender', None))
        self.message = MessageAdapter(event.message) if getattr(event, 'message', None) else None

class MTProtoTeleBot:
    """Lớp điều khiển chính giả lập pyTelegramBotAPI chạy trên nền giao thức MTProto"""

    def __init__(
        self,
        api_id: int,
        api_hash: str,
        bot_token: Optional[str] = None,
        session_name: str = "telebot_mtproto",
        proxy: Optional[Union[dict, tuple]] = None
    ):
        """
        Khởi tạo MTProto Bot
        :param api_id: Telegram API ID (lấy từ my.telegram.org)
        :param api_hash: Telegram API HASH (lấy từ my.telegram.org)
        :param bot_token: Bot token (nếu chạy dưới quyền Bot @BotFather). Để trống nếu chạy chế độ Userbot.
        :param session_name: Tên tệp tin phiên làm việc session
        :param proxy: Cấu hình Proxy (SOCKS5, HTTP, hoặc MTProto Proxy)
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.bot_token = bot_token
        self.proxy = proxy
        self.client = TelegramClient(session_name, api_id, api_hash, proxy=proxy)
        self.message_handlers = []
        self.callback_handlers = []
        self.loop = None

    def message_handler(
        self,
        content_types: Optional[List[str]] = None,
        commands: Optional[List[str]] = None,
        regexp: Optional[str] = None,
        func: Optional[Callable[[Any], bool]] = None
    ):
        """
        Decorator đăng ký hàm xử lý tin nhắn tương tự pyTelegramBotAPI
        """
        def decorator(handler_func: Callable[[MessageAdapter], Any]):
            self.message_handlers.append({
                "func": handler_func,
                "content_types": [ct.lower() for ct in content_types] if content_types else None,
                "commands": [c.lower() for c in commands] if commands else None,
                "regexp": regexp,
                "filter_func": func
            })
            return handler_func
        return decorator

    def callback_query_handler(self, func: Optional[Callable[[CallbackQueryAdapter], bool]] = None):
        """
        Decorator đăng ký hàm xử lý nút bấm Inline (Callback Query)
        """
        def decorator(handler_func: Callable[[CallbackQueryAdapter], Any]):
            self.callback_handlers.append({
                "func": handler_func,
                "filter_func": func
            })
            return handler_func
        return decorator

    async def _handle_message_update(self, event):
        """Hàm xử lý và lọc sự kiện tin nhắn nội bộ"""
        msg = event.message
        if not msg:
            return

        sender = await event.get_sender()
        adapted_msg = MessageAdapter(msg, sender)

        text_lower = adapted_msg.text.strip().lower()
        is_command = text_lower.startswith("/")
        command_name = text_lower.split()[0][1:] if is_command else ""

        for handler in self.message_handlers:
            # Lọc theo content_types
            if handler["content_types"] is not None:
                if adapted_msg.content_type not in handler["content_types"]:
                    continue

            # Lọc theo commands
            if handler["commands"] is not None:
                if not is_command or command_name not in handler["commands"]:
                    continue
            
            # Lọc theo regexp
            if handler["regexp"] is not None:
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
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, handler["func"], adapted_msg)

    async def _handle_callback_update(self, event):
        """Hàm xử lý sự kiện CallbackQuery cho nút bấm Inline"""
        adapted_cb = CallbackQueryAdapter(event)
        for handler in self.callback_handlers:
            if handler["filter_func"] is not None:
                try:
                    if not handler["filter_func"](adapted_cb):
                        continue
                except Exception:
                    continue

            if asyncio.iscoroutinefunction(handler["func"]):
                await handler["func"](adapted_cb)
            else:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, handler["func"], adapted_cb)

    def _execute_coro(self, coro):
        """Helper hỗ trợ gọi coroutine cho cả môi trường sync và async"""
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop and running_loop.is_running():
            return asyncio.ensure_future(coro)
        else:
            if self.loop and self.loop.is_running():
                return asyncio.run_coroutine_threadsafe(coro, self.loop)
            return asyncio.get_event_loop().run_until_complete(coro)

    def _parse_reply_markup(self, reply_markup: Any):
        """Chuyển đổi reply_markup custom sang chuẩn Telethon"""
        if reply_markup is None:
            return None
        if hasattr(reply_markup, 'to_telethon'):
            return reply_markup.to_telethon()
        return reply_markup

    def start(self):
        """Khởi động client và đăng ký sự kiện"""
        self.client.add_event_handler(self._handle_message_update, events.NewMessage(incoming=True))
        self.client.add_event_handler(self._handle_callback_update, events.CallbackQuery())
        
        if self.bot_token:
            self.client.start(bot_token=self.bot_token)
        else:
            self.client.start()
        
        self.loop = self.client.loop

    def run(self):
        """Bắt đầu chạy bot (blocking)"""
        self.start()
        print("Bot is running over MTProto...")
        self.client.run_until_disconnected()

    # --- API Action Methods ---

    def send_message(
        self,
        chat_id: Union[int, str],
        text: str,
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[Any] = None
    ) -> Any:
        """Gửi tin nhắn văn bản"""
        buttons = self._parse_reply_markup(reply_markup)
        return self._execute_coro(self.client.send_message(chat_id, text, reply_to=reply_to_message_id, buttons=buttons))

    def reply_to(self, message: MessageAdapter, text: str, reply_markup: Optional[Any] = None) -> Any:
        """Trả lời trực tiếp một tin nhắn"""
        return self.send_message(message.chat.id, text, reply_to_message_id=message.message_id, reply_markup=reply_markup)

    def send_document(
        self,
        chat_id: Union[int, str],
        file_path: str,
        caption: Optional[str] = None,
        reply_markup: Optional[Any] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Any:
        """Gửi tài liệu/tệp tin (Hỗ trợ file cực lớn lên tới 2GB/4GB và Progress Callback)"""
        buttons = self._parse_reply_markup(reply_markup)
        return self._execute_coro(self.client.send_file(
            chat_id, file_path, caption=caption, force_document=True, buttons=buttons, progress_callback=progress_callback
        ))

    def send_photo(
        self,
        chat_id: Union[int, str],
        file_path: str,
        caption: Optional[str] = None,
        reply_markup: Optional[Any] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Any:
        """Gửi hình ảnh"""
        buttons = self._parse_reply_markup(reply_markup)
        return self._execute_coro(self.client.send_file(
            chat_id, file_path, caption=caption, buttons=buttons, progress_callback=progress_callback
        ))

    def send_video(
        self,
        chat_id: Union[int, str],
        file_path: str,
        caption: Optional[str] = None,
        reply_markup: Optional[Any] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Any:
        """Gửi video"""
        buttons = self._parse_reply_markup(reply_markup)
        return self._execute_coro(self.client.send_file(
            chat_id, file_path, caption=caption, buttons=buttons, progress_callback=progress_callback
        ))

    def send_audio(
        self,
        chat_id: Union[int, str],
        file_path: str,
        caption: Optional[str] = None,
        reply_markup: Optional[Any] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Any:
        """Gửi file âm thanh (Audio)"""
        buttons = self._parse_reply_markup(reply_markup)
        return self._execute_coro(self.client.send_file(
            chat_id, file_path, caption=caption, buttons=buttons, progress_callback=progress_callback
        ))

    def send_voice(
        self,
        chat_id: Union[int, str],
        file_path: str,
        caption: Optional[str] = None,
        reply_markup: Optional[Any] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Any:
        """Gửi tin nhắn thoại (Voice note)"""
        buttons = self._parse_reply_markup(reply_markup)
        return self._execute_coro(self.client.send_file(
            chat_id, file_path, caption=caption, voice_note=True, buttons=buttons, progress_callback=progress_callback
        ))

    def send_sticker(self, chat_id: Union[int, str], file_path: str) -> Any:
        """Gửi nhãn dán (Sticker)"""
        return self._execute_coro(self.client.send_file(chat_id, file_path))

    def send_location(self, chat_id: Union[int, str], latitude: float, longitude: float) -> Any:
        """Gửi vị trí địa lý (Location)"""
        from telethon.tl.types import InputGeoPoint
        return self._execute_coro(self.client.send_file(chat_id, InputGeoPoint(latitude, longitude)))

    def download_file(
        self,
        message: MessageAdapter,
        dest_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Any:
        """Tải tệp đính kèm trong tin nhắn về máy với Progress Callback"""
        return self._execute_coro(self.client.download_media(message.raw, file=dest_path, progress_callback=progress_callback))

    def answer_callback_query(self, callback_query_id: str, text: Optional[str] = None, show_alert: bool = False) -> Any:
        """Phản hồi sự kiện nhấn nút Inline button (Callback Query)"""
        return self._execute_coro(self.client.answer_callback_query(callback_query_id, message=text, alert=show_alert))

    def edit_message_text(
        self,
        chat_id: Union[int, str],
        message_id: int,
        text: str,
        reply_markup: Optional[Any] = None
    ) -> Any:
        """Chỉnh sửa nội dung tin nhắn đã gửi"""
        buttons = self._parse_reply_markup(reply_markup)
        return self._execute_coro(self.client.edit_message(chat_id, message_id, text, buttons=buttons))

    def delete_message(self, chat_id: Union[int, str], message_id: int) -> Any:
        """Xóa tin nhắn"""
        return self._execute_coro(self.client.delete_messages(chat_id, message_id))

    def forward_message(self, chat_id: Union[int, str], from_chat_id: Union[int, str], message_id: int) -> Any:
        """Chuyển tiếp tin nhắn"""
        return self._execute_coro(self.client.forward_messages(chat_id, message_id, from_chat_id))
