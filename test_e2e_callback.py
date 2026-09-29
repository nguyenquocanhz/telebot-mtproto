# -*- coding: utf-8 -*-
"""
End-to-End (E2E) & Integration Tests for telebot_mtproto Callback Query handling.
Kiểm tra toàn diện xử lý sự kiện bấm nút Inline (CallbackQuery) từ lớp giao thức MTProto đến Bot Handler.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telethon.tl.types import UpdateBotCallbackQuery, PeerUser, User as TelethonUser, Message as TelethonMessage
from telethon import events
from telethon.tl.functions.messages import SetBotCallbackAnswerRequest

from telebot_mtproto.bot import MTProtoTeleBot, CallbackQueryAdapter, UserAdapter, MessageAdapter
from telebot_mtproto.types import InlineKeyboardMarkup, InlineKeyboardButton


@pytest.fixture
def mock_telethon_event():
    """Tạo đối tượng Event CallbackQuery thực tế của Telethon bao bọc UpdateBotCallbackQuery"""
    raw_update = UpdateBotCallbackQuery(
        query_id=987654321012345,
        user_id=12345678,
        peer=PeerUser(12345678),
        msg_id=1001,
        chat_instance=999888777,
        data=b"menu_catalog"
    )
    # Khởi tạo Telethon Event như cách Telethon dispatch khi nhận update từ server Telegram
    event = events.CallbackQuery.Event(raw_update, PeerUser(12345678), 1001)
    
    # Mock các coroutine của Telethon event
    mock_sender = TelethonUser(
        id=12345678,
        first_name="Nguyen",
        last_name="Van A",
        username="nguyenvana"
    )
    mock_msg = MagicMock(spec=TelethonMessage)
    mock_msg.id = 1001
    mock_msg.chat_id = 12345678
    mock_msg.message = "Menu text"
    mock_msg.media = None
    mock_msg.is_reply = False

    event.get_sender = AsyncMock(return_value=mock_sender)
    event.get_message = AsyncMock(return_value=mock_msg)
    event.answer = AsyncMock()

    return event


def test_callback_query_adapter_with_update_bot_callback_query(mock_telethon_event):
    """
    Test Case 1: Tái hiện lỗi gốc 'UpdateBotCallbackQuery object has no attribute id'
    và kiểm tra CallbackQueryAdapter trích xuất an toàn query_id, data, sender, message.
    """
    cb = CallbackQueryAdapter(mock_telethon_event)

    # 1. ID phải được lấy chính xác dưới dạng chuỗi (không bị AttributeError)
    assert cb.id == "987654321012345"
    assert isinstance(cb.id, str)

    # 2. Data nút bấm phải được decode từ bytes sang str
    assert cb.data == "menu_catalog"

    # 3. User ID fallback từ sender_id hoặc query.user_id khi chưa await get_sender()
    assert cb.from_user.id == 12345678

    # 4. Fallback message khi chưa có MessageAdapter
    assert cb.message is not None
    assert cb.message.chat.id == 12345678
    assert cb.message.message_id == 1001


def test_callback_query_adapter_with_sender_and_message(mock_telethon_event):
    """
    Test Case 2: Kiểm tra khi _handle_callback_update đã fetch sender & message
    """
    sender = TelethonUser(id=12345678, first_name="Anh", last_name="Tester", username="anhtester")
    msg = MagicMock(spec=TelethonMessage)
    msg.id = 1001
    msg.chat_id = -100123456789
    msg.message = "Xin chào"
    msg.media = None
    msg.is_reply = False

    cb = CallbackQueryAdapter(mock_telethon_event, sender=sender, message=msg)

    assert cb.id == "987654321012345"
    assert cb.from_user.id == 12345678
    assert cb.from_user.first_name == "Anh"
    assert cb.from_user.last_name == "Tester"
    assert cb.from_user.username == "anhtester"
    assert cb.message.chat.id == -100123456789
    assert cb.message.message_id == 1001
    assert cb.message.text == "Xin chào"


def test_callback_query_adapter_fallback_resilience():
    """
    Test Case 3: Kiểm tra độ bền (resilience) với các object dị biệt:
    raw object không có id property, không có query.id, chỉ có query_id.
    """
    class RawQueryOnly:
        class query:
            query_id = 555666777
            user_id = 9999
            chat_instance = 1111
        data = "btn_test"
        chat_id = 9999
        message_id = 200

    raw_ev = RawQueryOnly()
    cb = CallbackQueryAdapter(raw_ev)
    assert cb.id == "555666777"
    assert cb.data == "btn_test"
    assert cb.from_user.id == 9999
    assert cb.message.chat.id == 9999
    assert cb.message.message_id == 200


def test_e2e_handle_callback_update_flow(mock_telethon_event):
    """
    Test Case 4 (E2E): Kiểm tra luồng hoàn chỉnh _handle_callback_update -> callback_query_handler
    """
    async def run():
        with patch("telebot_mtproto.bot.TelegramClient"):
            bot = MTProtoTeleBot(api_id=12345, api_hash="fake_hash", bot_token="fake:token")

        handled_call = None

        @bot.callback_query_handler(func=lambda c: c.data == "menu_catalog")
        def handle_catalog(call):
            nonlocal handled_call
            handled_call = call

        # Thực thi callback update
        await bot._handle_callback_update(mock_telethon_event)

        # Đảm bảo handler đã nhận được CallbackQueryAdapter và các trường dữ liệu đầy đủ
        assert handled_call is not None
        assert handled_call.id == "987654321012345"
        assert handled_call.data == "menu_catalog"
        assert handled_call.from_user.id == 12345678
        assert handled_call.from_user.first_name == "Nguyen"
        assert handled_call.message.chat.id == 12345678
        assert handled_call.message.message_id == 1001

    asyncio.run(run())


def test_e2e_answer_callback_query():
    """
    Test Case 5 (E2E): Kiểm tra hàm answer_callback_query gửi đúng SetBotCallbackAnswerRequest
    tới client MTProto mà không gọi nhầm phương thức client.answer_callback_query không tồn tại.
    """
    async def run():
        with patch("telebot_mtproto.bot.TelegramClient") as MockClientClass:
            mock_client = MockClientClass.return_value
            mock_client.side_effect = AsyncMock(return_value=True)

            bot = MTProtoTeleBot(api_id=12345, api_hash="fake_hash", bot_token="fake:token")
            bot.client = mock_client

            # Gọi answer_callback_query
            bot.answer_callback_query("987654321012345", text="Đã xử lý!", show_alert=True)

            # Kiểm tra client đã được gọi với SetBotCallbackAnswerRequest
            assert mock_client.called
            call_arg = mock_client.call_args[0][0]
            assert isinstance(call_arg, SetBotCallbackAnswerRequest)
            assert call_arg.query_id == 987654321012345
            assert call_arg.message == "Đã xử lý!"
            assert call_arg.alert is True

    asyncio.run(run())


def test_e2e_sellerbot_main_handlers_integration(mock_telethon_event):
    """
    Test Case 6 (E2E Integration): Mô phỏng tương tác thực tế với logic của SellerBot main.py
    Khi user bấm nút Inline Menu, edit_message_text và answer_callback_query được gọi thành công.
    """
    async def run():
        with patch("telebot_mtproto.bot.TelegramClient") as MockClientClass:
            mock_client = MockClientClass.return_value
            mock_client.edit_message = AsyncMock(return_value=True)
            mock_client.side_effect = AsyncMock(return_value=True)

            bot = MTProtoTeleBot(api_id=12345, api_hash="fake_hash", bot_token="fake:token")
            bot.client = mock_client

            # Đăng ký handler tương tự trong main.py
            @bot.callback_query_handler(func=lambda c: True)
            def main_callback_handler(call):
                if call.data == "menu_catalog":
                    # Giả lập logic chuyển catalog
                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text="🛒 DANH SÁCH SẢN PHẨM KHẢ DỤNG"
                    )
                elif call.data == "prod_invalid":
                    # Giả lập sản phẩm không tồn tại
                    bot.answer_callback_query(call.id, text="Sản phẩm không tồn tại!", show_alert=True)

            # 1. User click "menu_catalog"
            mock_telethon_event.query.data = b"menu_catalog"
            await bot._handle_callback_update(mock_telethon_event)
            mock_client.edit_message.assert_called_once_with(
                12345678,
                1001,
                "🛒 DANH SÁCH SẢN PHẨM KHẢ DỤNG",
                buttons=None
            )

            # 2. User click sản phẩm không tồn tại
            mock_telethon_event.query.data = b"prod_invalid"
            await bot._handle_callback_update(mock_telethon_event)
            assert mock_client.called
            last_req = mock_client.call_args[0][0]
            assert isinstance(last_req, SetBotCallbackAnswerRequest)
            assert last_req.query_id == 987654321012345
            assert last_req.message == "Sản phẩm không tồn tại!"
            assert last_req.alert is True

    asyncio.run(run())


def test_e2e_direct_call_answer(mock_telethon_event):
    """
    Test Case 7 (E2E): Kiểm tra tiện ích call.answer(...) trực tiếp trên CallbackQueryAdapter.
    """
    async def run():
        cb = CallbackQueryAdapter(mock_telethon_event)
        task = cb.answer(text="Xác nhận!", show_alert=False)
        assert task is not None
        await task
        mock_telethon_event.answer.assert_called_once_with(
            message="Xác nhận!",
            alert=False,
            cache_time=0,
            url=None
        )

    asyncio.run(run())


def test_callback_query_unicode_data():
    """
    Test Case 8: Kiểm tra giải mã UTF-8 an toàn với tiếng Việt có dấu và Emoji
    """
    class RawUnicodeQuery:
        class query:
            query_id = 112233
            user_id = 4455
            chat_instance = 6677
        data = "sản_phẩm_đặc_biệt_⭐".encode('utf-8')
        chat_id = 4455
        message_id = 99

    cb = CallbackQueryAdapter(RawUnicodeQuery())
    assert cb.data == "sản_phẩm_đặc_biệt_⭐"
    assert cb.id == "112233"
