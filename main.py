# -*- coding: utf-8 -*-
# SellerBot Application using telebot-mtproto SDK (v1.2.0)

import os
import sys
from telebot_mtproto import MTProtoTeleBot
from telebot_mtproto.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
import config

# Khởi tạo Bot
bot = MTProtoTeleBot(
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN
)

def build_main_menu() -> InlineKeyboardMarkup:
    """Tạo bàn phím Inline Menu chính"""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🛒 Danh mục Sản phẩm", callback_data="menu_catalog"),
        InlineKeyboardButton("💳 Nạp tiền Tự động", callback_data="menu_deposit"),
        InlineKeyboardButton("👤 Tài khoản của tôi", callback_data="menu_profile"),
        InlineKeyboardButton("📜 Lịch sử mua hàng", callback_data="menu_history"),
        InlineKeyboardButton("💬 Hỗ trợ CSKH", url="https://t.me/telegram")
    )
    return markup

# --- Message Handlers ---

@bot.message_handler(commands=['start', 'menu'])
def send_welcome(message):
    user = db.get_user(message.from_user.id, message.from_user.first_name)
    welcome_text = (
        f"👋 **Xin chào {user['name']}!**\n"
        f"Chào mừng bạn đến với **SellerBot MTProto** - Hệ thống tự động 24/7!\n\n"
        f"🆔 **ID người dùng**: `{user['id']}`\n"
        f"💰 **Số dư tài khoản**: **{user['balance']:,} VNĐ**\n\n"
        f"Vui lòng chọn một tùy chọn bên dưới để bắt đầu mua sắm:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=build_main_menu())

@bot.message_handler(commands=['profile', 'me'])
def show_profile_command(message):
    user = db.get_user(message.from_user.id, message.from_user.first_name)
    profile_text = (
        f"👤 **THÔNG TIN TÀI KHOẢN**\n\n"
        f"🔹 **Họ tên**: {user['name']}\n"
        f"🔹 **Telegram ID**: `{user['id']}`\n"
        f"🔹 **Số dư khả dụng**: **{user['balance']:,} VNĐ**\n"
        f"🔹 **Ngày tham gia**: {user['created_at']}\n"
    )
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("💳 Nạp tiền ngay", callback_data="menu_deposit"),
        InlineKeyboardButton("🏠 Menu chính", callback_data="menu_main")
    )
    bot.send_message(message.chat.id, profile_text, reply_markup=markup)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id not in config.ADMIN_IDS:
        bot.reply_to(message, "❌ Bạn không có quyền truy cập bảng quản trị!")
        return

    stats = db.get_stats()
    admin_text = (
        f"👑 **BẢNG QUẢN TRỊ ADMIN (SELLER BOT)**\n\n"
        f"👥 **Tổng khách hàng**: `{stats['total_users']}` người\n"
        f"📦 **Tổng đơn đã bán**: `{stats['total_orders']}` đơn\n"
        f"💵 **Tổng doanh thu**: **{stats['total_revenue']:,} VNĐ**\n\n"
        f"📌 **Lệnh Admin**: `/addbalance <user_id> <số_tiền>`"
    )
    bot.send_message(message.chat.id, admin_text)

@bot.message_handler(commands=['addbalance'])
def add_balance_command(message):
    if message.from_user.id not in config.ADMIN_IDS:
        return

    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "⚠️ **Cú pháp**: `/addbalance <user_id> <số_tiền>`")
        return

    try:
        target_uid = int(parts[1])
        amount = int(parts[2])
        new_balance = db.update_balance(target_uid, amount)
        bot.reply_to(message, f"✅ Đã cộng **{amount:,} VNĐ** cho user `{target_uid}`. Số dư mới: **{new_balance:,} VNĐ**.")
        # Thông báo cho user
        bot.send_message(target_uid, f"🎉 Bạn đã được Admin nạp **{amount:,} VNĐ** vào tài khoản! Số dư mới: **{new_balance:,} VNĐ**.")
    except Exception as e:
        bot.reply_to(message, f"❌ Lỗi thực thi: {str(e)}")

# --- Callback Query Handlers (Inline Buttons) ---

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    data = call.data
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    if data == "menu_main":
        user = db.get_user(user_id, call.from_user.first_name)
        welcome_text = (
            f"👋 **Xin chào {user['name']}!**\n"
            f"Chào mừng bạn đến với **SellerBot MTProto** - Hệ thống tự động 24/7!\n\n"
            f"🆔 **ID người dùng**: `{user['id']}`\n"
            f"💰 **Số dư tài khoản**: **{user['balance']:,} VNĐ**\n\n"
            f"Vui lòng chọn một tùy chọn bên dưới:"
        )
        bot.edit_message_text(chat_id, call.message.message_id, welcome_text, reply_markup=build_main_menu())

    elif data == "menu_profile":
        user = db.get_user(user_id, call.from_user.first_name)
        profile_text = (
            f"👤 **THÔNG TIN TÀI KHOẢN**\n\n"
            f"🔹 **Họ tên**: {user['name']}\n"
            f"🔹 **Telegram ID**: `{user['id']}`\n"
            f"🔹 **Số dư khả dụng**: **{user['balance']:,} VNĐ**\n"
            f"🔹 **Ngày tham gia**: {user['created_at']}\n"
        )
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("💳 Nạp tiền ngay", callback_data="menu_deposit"),
            InlineKeyboardButton("🏠 Menu chính", callback_data="menu_main")
        )
        bot.edit_message_text(chat_id, call.message.message_id, profile_text, reply_markup=markup)

    elif data == "menu_deposit":
        user = db.get_user(user_id, call.from_user.first_name)
        memo = f"NAP {user_id}"
        deposit_text = (
            f"💳 **HƯỚNG DẪN NẠP TIỀN TỰ ĐỘNG**\n\n"
            f"🏦 **Ngân hàng**: `{config.BANK_NAME}`\n"
            f"🔢 **Số tài khoản**: `{config.BANK_ACCOUNT_NO}`\n"
            f"👤 **Chủ tài khoản**: `{config.BANK_ACCOUNT_NAME}`\n"
            f"📝 **Nội dung chuyển khoản**: `{memo}` (Bắt buộc)\n\n"
            f"⚠️ **Lưu ý**: Chuyển đúng nội dung `{memo}` để hệ thống cộng tiền tự động sau 1-3 phút."
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🏠 Menu chính", callback_data="menu_main"))
        bot.edit_message_text(chat_id, call.message.message_id, deposit_text, reply_markup=markup)

    elif data == "menu_catalog":
        products = db.get_products()
        catalog_text = "🛒 **DANH SÁCH SẢN PHẨM KHẢ DỤNG**\n\nChọn sản phẩm bạn muốn xem chi tiết:"
        markup = InlineKeyboardMarkup(row_width=1)
        for pid, prod in products.items():
            stock_count = len(prod['stock'])
            stock_str = f"({stock_count} sản phẩm)" if stock_count > 0 else "(Hết hàng)"
            markup.add(InlineKeyboardButton(f"{prod['name']} - {prod['price']:,}đ {stock_str}", callback_data=f"prod_{pid}"))
        markup.add(InlineKeyboardButton("🏠 Menu chính", callback_data="menu_main"))
        bot.edit_message_text(chat_id, call.message.message_id, catalog_text, reply_markup=markup)

    elif data.startswith("prod_"):
        product_id = data.split("prod_")[1]
        prod = db.get_product(product_id)
        if not prod:
            bot.answer_callback_query(call.id, text="Sản phẩm không tồn tại!", show_alert=True)
            return

        stock_count = len(prod['stock'])
        detail_text = (
            f"📦 **{prod['name']}**\n\n"
            f"📝 **Mô tả**: {prod['description']}\n"
            f"💰 **Giá bán**: **{prod['price']:,} VNĐ**\n"
            f"📊 **Kho hàng**: {stock_count} sản phẩm sẵn có\n"
        )
        markup = InlineKeyboardMarkup(row_width=2)
        if stock_count > 0:
            markup.add(InlineKeyboardButton("🛒 MUA NGAY", callback_data=f"buy_{product_id}"))
        markup.add(
            InlineKeyboardButton("🔙 Danh mục", callback_data="menu_catalog"),
            InlineKeyboardButton("🏠 Menu chính", callback_data="menu_main")
        )
        bot.edit_message_text(chat_id, call.message.message_id, detail_text, reply_markup=markup)

    elif data.startswith("buy_"):
        product_id = data.split("buy_")[1]
        result = db.buy_product(user_id, product_id)
        if not result["success"]:
            bot.answer_callback_query(call.id, text=result["message"], show_alert=True)
            return

        order = result["order"]
        delivery_text = (
            f"🎉 **MUA HÀNG THÀNH CÔNG!**\n\n"
            f"🧾 **Mã đơn hàng**: `{order['id']}`\n"
            f"📦 **Sản phẩm**: {order['product_name']}\n"
            f"💰 **Thanh toán**: {order['price']:,} VNĐ\n"
            f"💵 **Số dư còn lại**: {result['new_balance']:,} VNĐ\n\n"
            f"🔑 **THÔNG TIN SẢN PHẨM / KEY**:\n"
            f"```\n{result['item']}\n```\n"
            f"Cảm ơn bạn đã tin tưởng dịch vụ!"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🏠 Menu chính", callback_data="menu_main"))
        bot.edit_message_text(chat_id, call.message.message_id, delivery_text, reply_markup=markup)

    elif data == "menu_history":
        orders = db.get_user_orders(user_id)
        if not orders:
            history_text = "📜 **LỊCH SỬ MUA HÀNG**\n\nBạn chưa mua sản phẩm nào."
        else:
            history_text = f"📜 **LỊCH SỬ MUA HÀNG ({len(orders)} đơn)**\n\n"
            for o in reversed(orders[-5:]):
                history_text += (
                    f"🔹 **{o['product_name']}** ({o['price']:,}đ)\n"
                    f"   • Mã đơn: `{o['id']}` - {o['time']}\n"
                    f"   • Nội dung: `{o['content']}`\n\n"
                )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🏠 Menu chính", callback_data="menu_main"))
        bot.edit_message_text(chat_id, call.message.message_id, history_text, reply_markup=markup)

if __name__ == "__main__":
    print("Starting SellerBot over MTProto...")
    bot.run()
