import logging
from datetime import datetime, timedelta
from typing import List
from decimal import Decimal
import httpx

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from tinkoff_client import TinkoffInvestmentsClient
from .menus import MenuManager
from .portfolio_handlers import PortfolioHandler
from .income_handlers import IncomeHandler
from .notification_handlers import NotificationHandler

logger = logging.getLogger(__name__)

class CommandHandlers:
    def __init__(self, bot):
        self.bot = bot
        self.menu_manager = MenuManager(bot)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            user_id = update.effective_user.id
            logger.info(f"User {user_id} started the bot")
            
            # Проверяем наличие API токена
            api_token = await self.bot.user_service.get_user_api_token(user_id)
            if not api_token:
                logger.info(f"User {user_id} has no API token")
                await self.menu_manager.show_token_setup(update.message)
                return
            
            # Проверяем валидность токена
            logger.info(f"Validating token for user {user_id}")
            is_token_valid = await self.bot.validate_user_token(user_id)
            if not is_token_valid:
                logger.warning(f"Token validation failed for user {user_id}")
                await update.message.reply_text(
                    "❌ Ваш API токен недействителен. Пожалуйста, установите новый токен с помощью /set_token"
                )
                await self.menu_manager.show_token_setup(update.message)
                return
            
            # Проверяем наличие выбранных счетов
            selected_accounts = await self.bot.user_service.get_user_accounts(user_id)
            if not selected_accounts:
                logger.info(f"User {user_id} has no selected accounts")
                await self.show_accounts_command(update, context)
                return
                
            # Проверяем доступность счетов
            client = await self.bot.get_tinkoff_client(user_id)
            if not client:
                await update.message.reply_text("❌ API токен не установлен.")
                return

            valid_accounts = []
            for account_id in selected_accounts:
                try:
                    is_valid = await client.validate_account(account_id)
                    if is_valid:
                        valid_accounts.append(account_id)
                except Exception as e:
                    logger.warning(f"Error validating account {account_id} for user {user_id}: {e}")
                    continue
            
            if not valid_accounts:
                logger.warning(f"User {user_id} has no valid accounts")
                await update.message.reply_text(
                    "❌ Все ранее выбранные счета больше недоступны. Пожалуйста, выберите счета заново."
                )
                await self.show_accounts_command(update, context)
                return
            
            # Обновляем список валидных счетов
            if len(valid_accounts) != len(selected_accounts):
                await self.bot.user_service.set_user_accounts(user_id, valid_accounts)
            
            await self.menu_manager.show_main_menu(update.message)
            
        except httpx.ReadError as e:
            logger.error(f"Network error in start_command for user {update.effective_user.id}: {e}")
            await update.message.reply_text(
                "🌐 Проблемы с подключением к Tinkoff API. "
                "Пожалуйста, проверьте интернет-соединение и попробуйте позже."
            )
        except Exception as e:
            logger.error(f"Error in start_command for user {update.effective_user.id}: {e}", exc_info=True)
            await update.message.reply_text(
                "😞 Не удалось запустить бота. Возможно, проблемы с сетью. Попробуйте позже."
            )

    async def set_token_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда для установки API токена"""
        await self.menu_manager.show_token_setup(update.message)

    async def show_accounts_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            await self.menu_manager.show_accounts(update.message)
        except httpx.ReadError as e:
            logger.error(f"Network error in show_accounts_command: {e}")
            await update.message.reply_text(
                "🌐 Проблемы с подключением к Tinkoff API. "
                "Пожалуйста, проверьте интернет-соединение и попробуйте позже."
            )
        except Exception as e:
            logger.error(f"Error in show_accounts_command: {e}")
            await update.message.reply_text("❌ Ошибка при получении списка счетов.")

    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Да, удалить", callback_data="confirm_clear_data"),
                InlineKeyboardButton("❌ Нет, отмена", callback_data="main_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "⚠️ *Подтверждение удаления*\n\n"
            "Вы уверены, что хотите удалить все ваши данные (API токен и выбранные счета)?\n"
            "Это действие нельзя отменить.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
📖 Помощь по боту инвестиций 📖

*Основные команды:*
/start - Главное меню
/set_token - Установить API токен
/accounts - Выбрать счета
/reset - Удалить все данные
/help - Эта справка

*Функциональность:*
• Портфель - текущие позиции и их стоимость
• Доходность - анализ доходности за разные периоды
• Облигации - доход от купонных выплат
• Операции - история всех операций
• Расходы - комиссии и прочие расходы
• Графики - визуализация доходности и капитала
• Общий рост - доход за все время

💡 Совет: Для начала работы установите API токен с помощью /set_token
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')


class MessageHandlers:
    def __init__(self, bot):
        self.bot = bot

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений (для ввода API токена)"""
        user_id = update.effective_user.id
        message_text = update.message.text
        
        # Проверяем, не является ли сообщение командой
        if message_text.startswith('/'):
            return
        
        # Предполагаем, что это API токен
        if len(message_text) > 20:  # Минимальная длина токена
            await self.process_api_token(update, message_text)
        else:
            await update.message.reply_text("❌ Неверный формат API токена. Попробуйте еще раз.")

    async def process_api_token(self, update: Update, token: str):
        """Обработка введенного API токена"""
        user_id = update.effective_user.id
        
        try:
            # Удаляем пробелы и лишние символы
            token = token.strip()
            
            # Проверяем базовый формат токена
            if not token or len(token) < 20:
                await update.message.reply_text("❌ Неверный формат API токена. Токен должен быть длиннее 20 символов.")
                return
            
            # Создаем временный клиент для проверки токена
            temp_client = TinkoffInvestmentsClient(token)
            
            await update.message.reply_text("⏳ Проверяю токен...")
            
            is_valid = await temp_client.validate_token()
            
            if not is_valid:
                await update.message.reply_text(
                    "❌ Неверный API токен. Проверьте:\n"
                    "• Правильность введенного токена\n"
                    "• Не истек ли срок действия токена\n"
                    "• Имеет ли токен права на чтение брокерского счета"
                )
                return
            
            # Сохраняем токен
            await self.bot.user_service.set_user_api_token(user_id, token)
            
            # Очищаем кэш клиента
            if user_id in self.bot.tinkoff_clients:
                del self.bot.tinkoff_clients[user_id]
            
            await update.message.reply_text(
                "✅ API токен успешно сохранен и проверен!\n\n"
                "Теперь выберите счета для работы:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 Выбрать счета", callback_data="change_account")]
                ])
            )
            
        except httpx.ReadError as e:
            logger.error(f"Network error while validating token for user {user_id}: {e}")
            await update.message.reply_text(
                "🌐 Проблемы с подключением к Tinkoff API. "
                "Пожалуйста, проверьте интернет-соединение и попробуйте позже."
            )
        except Exception as e:
            logger.error(f"Error processing API token for user {user_id}: {e}")
            await update.message.reply_text(
                "❌ Ошибка при проверке токена. Убедитесь, что:\n"
                "• Токен действителен\n"
                "• У вас есть доступ к Tinkoff Invest\n"
                "• Токен имеет необходимые разрешения"
            )


class CallbackHandlers:
    def __init__(self, bot):
        self.bot = bot
        self.menu_manager = MenuManager(bot)
        self.portfolio_handler = PortfolioHandler(bot)
        self.income_handler = IncomeHandler(bot)
        self.notification_handler = NotificationHandler(bot)

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        callback_data = query.data
        user_id = query.from_user.id

        try:
            if callback_data.startswith("toggle_account_"):
                await self._handle_account_toggle(query, callback_data, user_id)
            elif callback_data == "save_accounts":
                await self._handle_save_accounts(query, user_id)
            elif callback_data == "confirm_clear_data":
                await self._handle_clear_data(query, user_id)
            elif callback_data == "main_menu":
                await self.menu_manager.show_main_menu_query(query)
            elif callback_data == "change_account":
                await self.menu_manager.show_accounts_query(query)
            elif callback_data == "portfolio":
                await self.portfolio_handler.show_portfolio(query)
            elif callback_data == "income_menu":
                await self.income_handler.show_income_menu(query)
            elif callback_data.startswith("income_"):
                period = callback_data.split("_")[1]
                await self.income_handler.show_income_period(query, period)
            elif callback_data == "total_growth":
                await self.income_handler.show_total_growth(query)
            elif callback_data == "bond_income":
                await self.income_handler.show_bond_income(query)
            elif callback_data == "expenses":
                await self.income_handler.show_expenses(query)
            elif callback_data == "operations":
                await self.portfolio_handler.show_operations_page(query, page=0)
            elif callback_data.startswith("operations_page_"):
                page = int(callback_data.replace("operations_page_", ""))
                await self.portfolio_handler.show_operations_page(query, page)
            elif callback_data == "positions":
                await self.portfolio_handler.show_positions_page(query, page=0)
            elif callback_data.startswith("positions_page_"):
                page = int(callback_data.replace("positions_page_", ""))
                await self.portfolio_handler.show_positions_page(query, page)
            elif callback_data == "help":
                await self.menu_manager.show_help(query)
            elif callback_data == "manage_token":
                await self.menu_manager.show_token_management(query)
            elif callback_data == "delete_token_confirm":
                await self.menu_manager.show_delete_token_confirmation(query)
            elif callback_data == "delete_token":
                await self._handle_delete_token(query, user_id)
            elif callback_data == "notifications_menu":
                await self.notification_handler.show_notifications_menu(query)
            elif callback_data == "test_daily_summary":
                await self.notification_handler.test_daily_summary(query)
            elif callback_data == "test_upcoming_payments":
                await self.notification_handler.test_upcoming_payments(query)
            elif callback_data == "no_action":
                pass  # Ничего не делаем для кнопок-заглушек
                
        except httpx.ReadError as e:
            logger.error(f"Network error in button_handler for user {user_id}: {e}")
            await query.edit_message_text(
                "🌐 Проблемы с подключением к Tinkoff API. "
                "Пожалуйста, проверьте интернет-соединение и попробуйте позже."
            )
        except Exception as e:
            logging.error(f"Error in button_handler for user {user_id}: {e}")
            await query.edit_message_text("😞 Произошла ошибка. Попробуйте позже.")

    async def _handle_account_toggle(self, query, callback_data, user_id):
        """Обработка переключения счета"""
        account_id = callback_data.replace("toggle_account_", "")
        
        # Получаем текущие выбранные счета
        selected_accounts = await self.bot.user_service.get_user_accounts(user_id)
        
        if account_id in selected_accounts:
            await self.bot.user_service.remove_user_account(user_id, account_id)
        else:
            await self.bot.user_service.add_user_account(user_id, account_id)
        
        # Обновляем сообщение
        await self.menu_manager.show_accounts_query(query)

    async def _handle_save_accounts(self, query, user_id):
        """Обработка сохранения счетов"""
        selected_accounts = await self.bot.user_service.get_user_accounts(user_id)
        
        if not selected_accounts:
            await query.edit_message_text(
                "❌ Вы не выбрали ни одного счета. Пожалуйста, выберите хотя бы один счет.",
                parse_mode='Markdown'
            )
            return
        
        await query.edit_message_text(
            f"✅ *Счета успешно сохранены!*\n\n"
            f"Выбрано счетов: {len(selected_accounts)}\n\n"
            f"Теперь вы можете просматривать портфель и операции по выбранным счетам.\n"
            f"Используйте кнопки ниже для навигации.",
            parse_mode='Markdown'
        )
        await self.menu_manager.show_main_menu_query(query)

    async def _handle_clear_data(self, query, user_id):
        """Обработка очистки данных"""
        await self.bot.user_service.clear_user_data(user_id)
        if user_id in self.bot.tinkoff_clients:
            del self.bot.tinkoff_clients[user_id]
        if user_id in self.bot.user_pagination_data:
            del self.bot.user_pagination_data[user_id]
        
        await query.edit_message_text(
            "✅ *Все данные успешно удалены!*\n\n"
            "Для начала работы заново используйте /start",
            parse_mode='Markdown'
        )

    async def _handle_delete_token(self, query, user_id):
        """Обработка удаления токена"""
        await self.bot.user_service.clear_user_data(user_id)
        if user_id in self.bot.tinkoff_clients:
            del self.bot.tinkoff_clients[user_id]
        await query.edit_message_text("✅ API токен и все данные удалены. Используйте /set_token для установки нового токена.")
        