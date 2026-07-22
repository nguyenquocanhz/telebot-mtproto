# -*- coding: utf-8 -*-
# Database manager for SellerBot

import json
import os
import time
from typing import Dict, List, Optional, Any

DB_FILE = "sellerbot_db.json"

DEFAULT_DATA = {
    "users": {},
    "products": {
        "chatgpt_plus": {
            "id": "chatgpt_plus",
            "name": "🤖 Tài khoản ChatGPT Plus 1 Tháng",
            "price": 150000,
            "category": "accounts",
            "description": "Tài khoản ChatGPT Plus dùng chung 30 ngày, truy cập GPT-4, DALL-E 3.",
            "stock": [
                "acc1@chatgpt.com | Pass: 123456 | PIN: 1111",
                "acc2@chatgpt.com | Pass: 654321 | PIN: 2222"
            ]
        },
        "netflix_4k": {
            "id": "netflix_4k",
            "name": "🎬 Profile Netflix 4K UHD 1 Tháng",
            "price": 70000,
            "category": "accounts",
            "description": "Profile riêng tư xem phim 4K Ultra HD 30 ngày.",
            "stock": [
                "acc1@netflix.com | Pass: netflix123 | Profile: VIP1 | PIN: 9999"
            ]
        },
        "canva_pro": {
            "id": "canva_pro",
            "name": "🎨 Upgrade Canva Pro 1 Năm",
            "price": 99000,
            "category": "keys",
            "description": "Nâng cấp Canva Pro chính chủ dùng 1 năm.",
            "stock": [
                "Link tham gia đội nhóm Canva Pro: https://canva.com/brand/join?code=MOCK_KEY_123"
            ]
        },
        "vps_high": {
            "id": "vps_high",
            "name": "⚡ VPS Windows 4GB RAM - 2 CPU",
            "price": 200000,
            "category": "vps",
            "description": "VPS Windows Server 2022 tốc độ cao, băng thông không giới hạn 30 ngày.",
            "stock": [
                "IP: 103.1.2.3 | User: Administrator | Pass: VpsSecret@2026"
            ]
        }
    },
    "orders": []
}

class Database:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self._load()

    def _load(self):
        if not os.path.exists(self.db_path):
            self.data = DEFAULT_DATA
            self._save()
        else:
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = DEFAULT_DATA
                self._save()

    def _save(self):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    def get_user(self, user_id: int, first_name: str = "") -> Dict[str, Any]:
        uid_str = str(user_id)
        if uid_str not in self.data["users"]:
            self.data["users"][uid_str] = {
                "id": user_id,
                "name": first_name or "Khách hàng",
                "balance": 0,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            self._save()
        return self.data["users"][uid_str]

    def update_balance(self, user_id: int, amount: int) -> int:
        uid_str = str(user_id)
        user = self.get_user(user_id)
        user["balance"] += amount
        self._save()
        return user["balance"]

    def get_products(self) -> Dict[str, Dict[str, Any]]:
        return self.data["products"]

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        return self.data["products"].get(product_id)

    def buy_product(self, user_id: int, product_id: str) -> Dict[str, Any]:
        user = self.get_user(user_id)
        product = self.get_product(product_id)

        if not product:
            return {"success": False, "message": "❌ Sản phẩm không tồn tại!"}

        if user["balance"] < product["price"]:
            return {
                "success": False,
                "message": f"❌ Số dư không đủ! Cần **{product['price']:,} VNĐ**, số dư hiện tại: **{user['balance']:,} VNĐ**."
            }

        if not product["stock"]:
            return {"success": False, "message": "❌ Sản phẩm hiện tại đang hết hàng!"}

        # Trừ tiền & lấy item từ kho
        item = product["stock"].pop(0)
        user["balance"] -= product["price"]

        # Lưu đơn hàng
        order = {
            "id": f"ORD{int(time.time())}",
            "user_id": user_id,
            "product_name": product["name"],
            "price": product["price"],
            "content": item,
            "time": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.data["orders"].append(order)
        self._save()

        return {
            "success": True,
            "item": item,
            "order": order,
            "new_balance": user["balance"]
        }

    def get_user_orders(self, user_id: int) -> List[Dict[str, Any]]:
        return [o for o in self.data["orders"] if o["user_id"] == user_id]

    def get_stats(self) -> Dict[str, Any]:
        total_users = len(self.data["users"])
        total_orders = len(self.data["orders"])
        total_revenue = sum(o["price"] for o in self.data["orders"])
        return {
            "total_users": total_users,
            "total_orders": total_orders,
            "total_revenue": total_revenue
        }

db = Database()
