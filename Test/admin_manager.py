import json
import os
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class AdminManager:
    def __init__(self):
        self.admin_file = "admins.json"
        self.user_messages_file = "user_messages.json"
        self.load_admins()
        self.load_user_messages()

    def load_admins(self):
        """Загрузка списка админов"""
        try:
            if os.path.exists(self.admin_file):
                with open(self.admin_file, 'r', encoding='utf-8') as f:
                    self.admins = set(json.load(f))
            else:
                self.admins = set()
                self.save_admins()
        except Exception as e:
            logger.error(f"Error loading admins: {e}")
            self.admins = set()

    def load_user_messages(self):
        """Загрузка сообщений пользователей"""
        try:
            if os.path.exists(self.user_messages_file):
                with open(self.user_messages_file, 'r', encoding='utf-8') as f:
                    self.user_messages = json.load(f)
            else:
                self.user_messages = {}
                self.save_user_messages()
        except Exception as e:
            logger.error(f"Error loading user messages: {e}")
            self.user_messages = {}

    def save_admins(self):
        """Сохранение списка админов"""
        try:
            with open(self.admin_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.admins), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving admins: {e}")

    def save_user_messages(self):
        """Сохранение сообщений пользователей"""
        try:
            with open(self.user_messages_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_messages, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving user messages: {e}")

    def is_admin(self, user_id: int) -> bool:
        """Проверка, является ли пользователь админом"""
        return user_id in self.admins or user_id in Config.ADMIN_IDS

    def add_admin(self, user_id: int):
        """Добавить админа"""
        self.admins.add(user_id)
        self.save_admins()

    def remove_admin(self, user_id: int):
        """Удалить админа"""
        self.admins.discard(user_id)
        self.save_admins()

    def get_admins(self) -> List[int]:
        """Получить список всех админов"""
        return list(self.admins) + Config.ADMIN_IDS

    def add_user_message(self, user_id: int, username: str, message: str):
        """Добавить сообщение от пользователя"""
        if user_id not in self.user_messages:
            self.user_messages[user_id] = {
                'username': username,
                'messages': []
            }
        
        self.user_messages[user_id]['messages'].append({
            'text': message,
            'timestamp': os.times().elapsed,
            'answered': False
        })
        self.save_user_messages()

    def get_unanswered_messages(self) -> Dict:
        """Получить неотвеченные сообщения"""
        unanswered = {}
        for user_id, data in self.user_messages.items():
            user_unanswered = [msg for msg in data['messages'] if not msg['answered']]
            if user_unanswered:
                unanswered[user_id] = {
                    'username': data['username'],
                    'messages': user_unanswered
                }
        return unanswered

    def mark_message_answered(self, user_id: int, message_index: int):
        """Пометить сообщение как отвеченное"""
        if user_id in self.user_messages and message_index < len(self.user_messages[user_id]['messages']):
            self.user_messages[user_id]['messages'][message_index]['answered'] = True
            self.save_user_messages()
            