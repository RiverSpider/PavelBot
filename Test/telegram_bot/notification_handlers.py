import logging
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

class NotificationHandler:
    def __init__(self, bot):
        self.bot = bot

    async def show_notifications_menu(self, query):
        """Показать меню уведомлений для тестирования"""
        keyboard = [
            [
                InlineKeyboardButton("📊 Тест: Дневная сводка", callback_data="test_daily_summary"),
                InlineKeyboardButton("📅 Тест: Предстоящие выплаты", callback_data="test_upcoming_payments")
            ],
            [
                InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            "🔔 *Меню тестирования уведомлений*\n\n"
            "Здесь вы можете протестировать функционал уведомлений:\n\n"
            "• 📊 *Дневная сводка* - статистика операций за сегодня\n"
            "• 📅 *Предстоящие выплаты* - дивиденды и купоны на неделю\n\n"
            "⚠️ *В реальной работе:*\n"
            "• Дневная сводка приходит автоматически в 20:00\n"
            "• Уведомления о выплатах - по понедельникам в 13:00"
        )
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    async def test_daily_summary(self, query):
        """Тестирование ежедневной сводки"""
        try:
            user_id = query.from_user.id
            selected_accounts = await self.bot.user_service.get_user_accounts(user_id)
            
            if not selected_accounts:
                await query.edit_message_text("❌ Счета не выбраны.")
                return

            client = await self.bot.get_tinkoff_client(user_id)
            if not client:
                await query.edit_message_text("❌ API токен не установлен.")
                return

            await query.edit_message_text("⏳ Формирую дневную сводку...")
            
            daily_summary = await client.get_daily_summary(selected_accounts)
            message = await client.format_daily_summary_message(daily_summary)
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="notifications_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logging.error(f"Error in test_daily_summary: {e}")
            await query.edit_message_text("❌ Ошибка при формировании сводки.")

    async def test_upcoming_payments(self, query):
        """Тестирование уведомления о предстоящих выплатах"""
        try:
            user_id = query.from_user.id
            selected_accounts = await self.bot.user_service.get_user_accounts(user_id)
            
            if not selected_accounts:
                await query.edit_message_text("❌ Счета не выбраны.")
                return

            client = await self.bot.get_tinkoff_client(user_id)
            if not client:
                await query.edit_message_text("❌ API токен не установлен.")
                return

            await query.edit_message_text("⏳ Проверяю предстоящие выплаты...")
            
            upcoming_payments = await client.get_upcoming_payments(selected_accounts)
            message = await client.format_upcoming_payments_message(upcoming_payments)
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="notifications_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logging.error(f"Error in test_upcoming_payments: {e}")
            await query.edit_message_text("❌ Ошибка при проверке выплат.")
            