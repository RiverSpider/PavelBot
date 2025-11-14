import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)

class EncryptionService:
    def __init__(self, encryption_key: str):
        self.encryption_key = encryption_key
        self.fernet = self._create_fernet()
    
    def _create_fernet(self) -> Fernet:
        """Создание Fernet шифратора на основе ключа из .env"""
        try:
            key_bytes = self.encryption_key.encode()
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'salt_',
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(key_bytes))
            
            return Fernet(key)
        except Exception as e:
            logger.error(f"Error creating Fernet: {e}")
            raise
    
    def encrypt(self, data: str) -> str:
        """Шифрование данных"""
        try:
            encrypted_data = self.fernet.encrypt(data.encode())
            return encrypted_data.decode()
        except Exception as e:
            logger.error(f"Error encrypting data: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """Дешифрование данных"""
        try:
            decrypted_data = self.fernet.decrypt(encrypted_data.encode())
            return decrypted_data.decode()
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            raise
        