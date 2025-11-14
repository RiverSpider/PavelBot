import os
import asyncio
import logging
import re
from typing import Dict, Optional

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.request import HTTPXRequest
from telegram.error import NetworkError, TimedOut

from config import Config
from tinkoff_client import TinkoffInvestmentsClient
from Test.user_service import UserService
from .handlers import CommandHandlers, CallbackHandlers, MessageHandlers

logger = logging.getLogger(__name__)

class TelegramBotHandler:
    def __init__(self):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.user_service = UserService()
        
        # Кэш для клиентов Tinkoff (user_id -> TinkoffInvestmentsClient)
        self.tinkoff_clients: Dict[int, TinkoffInvestmentsClient] = {}
        self.user_pagination_data = {}
        
        # Используем более консервативные таймауты
        request = HTTPXRequest(
            connect_timeout=30.0,
            read_timeout=30.0,
            write_timeout=30.0,
            pool_timeout=30.0
        )
        
        self.application = Application.builder().token(self.token).request(request).build()
        
        # Инициализируем обработчики
        self.command_handlers = CommandHandlers(self)
        self.callback_handlers = CallbackHandlers(self)
        self.message_handlers = MessageHandlers(self)
        
        self.setup_handlers()
        self.setup_error_handler()

    def setup_handlers(self):
        """Настройка обработчиков"""
        # Команды
        self.application.add_handler(CommandHandler("start", self.command_handlers.start_command))
        self.application.add_handler(CommandHandler("help", self.command_handlers.help_command))
        self.application.add_handler(CommandHandler("accounts", self.command_handlers.show_accounts_command))
        self.application.add_handler(CommandHandler("reset", self.command_handlers.reset_command))
        self.application.add_handler(CommandHandler("set_token", self.command_handlers.set_token_command))
        
        # Callback queries
        self.application.add_handler(CallbackQueryHandler(self.callback_handlers.button_handler))
        
        # Текстовые сообщения
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handlers.handle_message))

    def setup_error_handler(self):
        """Настройка обработчика ошибок"""
        self.application.add_error_handler(self.error_handler)

    async def get_tinkoff_client(self, user_id: int) -> Optional[TinkoffInvestmentsClient]:
        """Получить клиент Tinkoff для пользователя"""
        if user_id in self.tinkoff_clients:
            return self.tinkoff_clients[user_id]
        
        api_token = await self.user_service.get_user_api_token(user_id)
        if not api_token:
            return None
        
        client = TinkoffInvestmentsClient(api_token)
        self.tinkoff_clients[user_id] = client
        return client

    async def validate_user_token(self, user_id: int) -> bool:
        """Проверка валидности токена пользователя"""
        try:
            client = await self.get_tinkoff_client(user_id)
            if not client:
                return False
            
            return await client.validate_token()
        except Exception as e:
            logger.error(f"Error validating token for user {user_id}: {e}")
            return False

    def escape_markdown(self, text: str) -> str:
        """Экранирование символов Markdown"""
        if not text:
            return text
            
        escape_chars = r'\_*[]()~`>#+-=|{}.!'
        return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        error = context.error
        
        # Логируем ошибку
        if isinstance(error, NetworkError):
            logger.warning(f"Network error: {error}")
        elif isinstance(error, TimedOut):
            logger.warning(f"Timeout error: {error}")
        else:
            logger.error(f"Exception while handling an update: {error}", exc_info=error)
        
        # Пытаемся отправить сообщение об ошибке пользователю
        try:
            if update and update.effective_chat:
                if isinstance(error, (NetworkError, TimedOut)):
                    error_text = (
                        "🌐 *Проблемы с сетью*\n\n"
                        "Не удалось отправить сообщение из-за проблем с интернет-соединением.\n"
                        "Пожалуйста, попробуйте еще раз через несколько секунд."
                    )
                else:
                    error_text = (
                        "😞 *Произошла ошибка*\n\n"
                        "При обработке вашего запроса произошла непредвиденная ошибка.\n"
                        "Пожалуйста, попробуйте еще раз или обратитесь в поддержку."
                    )
                
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=error_text,
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Error in error handler while sending message: {e}")

    async def safe_send_message(self, chat_id: int, text: str, **kwargs):
        """Безопасная отправка сообщения с повторными попытками"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await self.application.bot.send_message(chat_id=chat_id, text=text, **kwargs)
                return True
            except (NetworkError, TimedOut) as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Экспоненциальная задержка
                else:
                    logger.error(f"Failed to send message after {max_retries} attempts")
                    return False
            except Exception as e:
                logger.error(f"Unexpected error while sending message: {e}")
                return False
        return False

    def run(self):
        """Запуск бота"""
        print("🤖 Бот запущен!")
        print("⚠️  Если возникают проблемы с соединением, проверьте:")
        print("   - Доступ к api.telegram.org")
        print("   - Стабильность интернет-соединения") 
        print("   - Настройки брандмауэра")
        print("   - Правильность TELEGRAM_BOT_TOKEN в .env файле")
        print("   - Доступ к Tinkoff API (api-invest.tinkoff.ru)")
        
        try:
            self.application.run_polling(
                poll_interval=2.0,  # Уменьшаем интервал опроса
                timeout=20,
                drop_pending_updates=True,
                allowed_updates=['message', 'callback_query']
            )
        except Exception as e:
            logger.error(f"Failed to start bot: {e}")
            print(f"❌ Критическая ошибка запуска: {e}")
            print("🔄 Попытка перезапуска через 10 секунд...")
            import time
            time.sleep(10)
            self.run()  # Рекурсивный перезапуск
            