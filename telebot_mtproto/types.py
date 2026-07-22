# -*- coding: utf-8 -*-
# Types module for Telebot MTProto (types.py)

from typing import List, Optional, Union
from telethon import Button

class InlineKeyboardButton:
    """Nút bấm Inline Keyboard"""
    def __init__(self, text: str, callback_data: Optional[str] = None, url: Optional[str] = None):
        self.text = text
        self.callback_data = callback_data
        self.url = url

    def to_telethon(self):
        if self.url:
            return Button.url(self.text, self.url)
        elif self.callback_data:
            return Button.inline(self.text, data=self.callback_data.encode('utf-8'))
        return Button.inline(self.text)

class InlineKeyboardMarkup:
    """Bàn phím Inline (gắn kèm tin nhắn)"""
    def __init__(self, row_width: int = 3):
        self.row_width = row_width
        self.keyboard: List[List[InlineKeyboardButton]] = []

    def add(self, *args: InlineKeyboardButton):
        """Thêm các nút vào bàn phím (tự động xuống dòng theo row_width)"""
        row = []
        for btn in args:
            row.append(btn)
            if len(row) >= self.row_width:
                self.keyboard.append(row)
                row = []
        if row:
            self.keyboard.append(row)

    def row(self, *args: InlineKeyboardButton):
        """Thêm một hàng nút bấm"""
        self.keyboard.append(list(args))

    def to_telethon(self):
        """Chuyển đổi thành cấu trúc Button của Telethon"""
        telethon_grid = []
        for row in self.keyboard:
            telethon_row = [btn.to_telethon() for btn in row]
            telethon_grid.append(telethon_row)
        return telethon_grid

class KeyboardButton:
    """Nút bấm Reply Keyboard"""
    def __init__(self, text: str, request_contact: bool = False, request_location: bool = False):
        self.text = text
        self.request_contact = request_contact
        self.request_location = request_location

    def to_telethon(self):
        if self.request_contact:
            return Button.request_phone(self.text)
        elif self.request_location:
            return Button.request_location(self.text)
        return Button.text(self.text)

class ReplyKeyboardMarkup:
    """Bàn phím Reply Keyboard (thay thế bàn phím người dùng)"""
    def __init__(self, resize_keyboard: bool = True, one_time_keyboard: bool = False, row_width: int = 3):
        self.resize_keyboard = resize_keyboard
        self.one_time_keyboard = one_time_keyboard
        self.row_width = row_width
        self.keyboard: List[List[KeyboardButton]] = []

    def add(self, *args: KeyboardButton):
        row = []
        for btn in args:
            row.append(btn if isinstance(btn, KeyboardButton) else KeyboardButton(str(btn)))
            if len(row) >= self.row_width:
                self.keyboard.append(row)
                row = []
        if row:
            self.keyboard.append(row)

    def row(self, *args: KeyboardButton):
        self.keyboard.append([btn if isinstance(btn, KeyboardButton) else KeyboardButton(str(btn)) for btn in args])

    def to_telethon(self):
        telethon_grid = []
        for row in self.keyboard:
            telethon_row = [btn.to_telethon() for btn in row]
            telethon_grid.append(telethon_row)
        return telethon_grid

class ReplyKeyboardRemove:
    """Xóa bàn phím Reply Keyboard"""
    def to_telethon(self):
        return Button.clear()
