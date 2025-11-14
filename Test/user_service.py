import os
import json
import aiofiles
import logging
from typing import Optional, List, Dict
from config import Config
from encryption_service import EncryptionService

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self):
        self.data_dir = Config.USER_DATA_DIR
        self.encryption_service = EncryptionService(Config.ENCRYPTION_KEY)

    def _get_user_file_path(self, user_id: int) -> str:
        """Получить путь к файлу данных пользователя"""
        return os.path.join(self.data_dir, f"user_{user_id}.json")

    async def get_user_data(self, user_id: int) -> Dict:
        """Получить все данные пользователя"""
        try:
            file_path = self._get_user_file_path(user_id)
            if os.path.exists(file_path):
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    data = json.loads(await f.read())
                    if 'encrypted_api_token' in data:
                        try:
                            data['api_token'] = self.encryption_service.decrypt(data['encrypted_api_token'])
                        except Exception as e:
                            logger.error(f"Error decrypting token for user {user_id}: {e}")
                            data['api_token'] = None
                    return data
            return {}
        except Exception as e:
            logger.error(f"Error reading user data for {user_id}: {e}")
            return {}

    async def save_user_data(self, user_id: int, data: Dict):
        """Сохранить данные пользователя"""
        try:
            file_path = self._get_user_file_path(user_id)
            
            if 'api_token' in data and data['api_token']:
                data['encrypted_api_token'] = self.encryption_service.encrypt(data['api_token'])
                del data['api_token']
            
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error(f"Error saving user data for {user_id}: {e}")

    async def set_user_api_token(self, user_id: int, api_token: str):
        """Сохранить API токен пользователя"""
        data = await self.get_user_data(user_id)
        data['api_token'] = api_token
        await self.save_user_data(user_id, data)

    async def get_user_api_token(self, user_id: int) -> Optional[str]:
        """Получить API токен пользователя"""
        data = await self.get_user_data(user_id)
        return data.get('api_token')

    async def set_user_accounts(self, user_id: int, account_ids: List[str]):
        """Сохранить выбранные счета пользователя"""
        data = await self.get_user_data(user_id)
        data['selected_account_ids'] = account_ids
        await self.save_user_data(user_id, data)

    async def get_user_accounts(self, user_id: int) -> List[str]:
        """Получить выбранные счета пользователя"""
        data = await self.get_user_data(user_id)
        return data.get('selected_account_ids', [])

    async def clear_user_data(self, user_id: int):
        """Очистить все данные пользователя"""
        try:
            file_path = self._get_user_file_path(user_id)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.error(f"Error clearing user data for {user_id}: {e}")
            