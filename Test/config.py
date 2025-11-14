import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TINKOFF_API_TOKEN = os.getenv('TINKOFF_API_TOKEN')
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
    
    USER_DATA_DIR = "user_data"
    ADMIN_IDS = [int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]
    
    @classmethod
    def validate(cls):
        missing = []
        if not cls.TELEGRAM_BOT_TOKEN:
            missing.append('TELEGRAM_BOT_TOKEN')
        if not cls.TINKOFF_API_TOKEN:
            missing.append('TINKOFF_API_TOKEN')
        if not cls.ENCRYPTION_KEY:
            missing.append('ENCRYPTION_KEY')
        
        if missing:
            raise ValueError(f"Missing environment variables: {', '.join(missing)}")
        
        os.makedirs(cls.USER_DATA_DIR, exist_ok=True)
        