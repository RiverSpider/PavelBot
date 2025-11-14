import logging
from typing import List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

class IncomeHandler:
    def __init__(self, bot):
        self.bot = bot

    async def show_income_menu(self, query):
        try:
            keyboard = [
                [
                    InlineKeyboardButton("📅 За день", callback_data="income_day"),
                    InlineKeyboardButton("📅 За неделю", callback_data="income_week")
                ],
                [
                    InlineKeyboardButton("📅 За месяц", callback_data="income_month"),
                    InlineKeyboardButton("📅 За год", callback_data="income_year")
                ],
                [
                    InlineKeyboardButton("📅 За все время", callback_data="income_all_time")
                ],
                [
                    InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📊 *Анализ доходности* 📊\nВыберите период:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logging.error(f"Error in show_income_menu: {e}")
            await query.edit_message_text("❌ Ошибка при отображении меню доходности.")

    async def show_income_period(self, query, period):
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

            period_names = {'day': 'день', 'week': 'неделю', 'month': 'месяц', 'year': 'год', 'all_time': 'все время'}
            period_name = period_names.get(period, period)
            
            await query.edit_message_text(f"⏳ Рассчитываю доходность за {period_name}...")
            
            income_data = await client.calculate_income(selected_accounts, period)
            
            net_income = float(income_data['total_income'] - income_data['commission_expenses'])
            
            income_text = f"📈 *Доходность за {period_name}:*\n\n"
            income_text += f"💰 *Общий доход:* {float(income_data['total_income']):,.2f} ₽\n"
            income_text += f"🎯 *От облигаций:* {float(income_data['bond_income']):,.2f} ₽\n"
            income_text += f"💵 *От дивидендов:* {float(income_data['dividend_income']):,.2f} ₽\n"
            income_text += f"💸 *Комиссии:* {float(income_data['commission_expenses']):,.2f} ₽\n"
            income_text += f"💎 *Чистый доход:* {net_income:,.2f} ₽\n\n"
            income_text += f"📊 *Количество счетов:* {len(selected_accounts)}"
            
            await self._send_income_charts(query, selected_accounts, period, period_name, income_text)
            
        except Exception as e:
            logging.error(f"Error in show_income_period: {e}")
            await query.edit_message_text("❌ Ошибка при расчете доходности.")

    async def show_total_growth(self, query):
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

            await query.edit_message_text("⏳ Рассчитываю общий рост капитала за все время...")
            
            portfolio_data = await client.get_portfolio_summary(selected_accounts)
            current_capital = portfolio_data['total_value']
            
            growth_data = await client.calculate_total_capital_growth(selected_accounts)
            
            growth_text = "🚀 *Общий рост капитала за все время*\n\n"
            growth_text += f"💰 *Текущий капитал:* {current_capital:,.2f} ₽\n"
            growth_text += f"📊 *Количество счетов:* {len(selected_accounts)}\n\n"
            growth_text += f"📈 *Общий доход:* {float(growth_data['total_growth']):,.2f} ₽\n"
            growth_text += f"💼 *Вложено средств:* {float(growth_data['total_invested']):,.2f} ₽\n"
            growth_text += f"🏦 *Выведено средств:* {float(growth_data['total_withdrawn']):,.2f} ₽\n"
            growth_text += f"💎 *Чистый рост:* {float(growth_data['net_growth']):,.2f} ₽\n\n"
            
            if growth_data['total_invested'] > 0:
                roi = (growth_data['net_growth'] / growth_data['total_invested']) * 100
                growth_text += f"📊 *ROI (доходность):* {float(roi):.2f}%"
            
            await self._send_total_growth_chart(query, selected_accounts, growth_text)
            
        except Exception as e:
            logging.error(f"Error in show_total_growth: {e}")
            await query.edit_message_text("❌ Ошибка при расчете общего роста капитала.")

    async def show_bond_income(self, query):
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

            await query.edit_message_text("⏳ Загружаю данные по облигациям...")
            
            bond_data = await client.get_bond_payments_summary(selected_accounts)
            
            bond_text = "🎯 *Доход от выплат по облигациям* 🎯\n\n"
            bond_text += f"За последний год:\n"
            bond_text += f"💰 *Купонные выплаты:* {float(bond_data['bond_coupons']):,.2f} ₽\n"
            bond_text += f"📊 *Количество счетов:* {len(selected_accounts)}\n\n"
            bond_text += "Это суммарный доход от всех купонных выплат по вашим облигациям."
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(bond_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logging.error(f"Error in show_bond_income: {e}")
            await query.edit_message_text("❌ Ошибка при загрузке данных по облигациям.")

    async def show_expenses(self, query):
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

            await query.edit_message_text("⏳ Загружаю данные по расходам...")
            
            expenses_data = await client.get_total_expenses(selected_accounts)
            
            expenses_text = "💸 *Ваши расходы на инвестиции* 💸\n\n"
            expenses_text += f"За последний год:\n"
            expenses_text += f"📊 *Общие расходы* (комиссии): {float(expenses_data['total_expenses']):,.2f} ₽\n"
            expenses_text += f"📊 *Количество счетов:* {len(selected_accounts)}\n\n"
            expenses_text += "💡 *Совет:* Следите за комиссиями - они могут существенно влиять на итоговую доходность!"
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(expenses_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logging.error(f"Error in show_expenses: {e}")
            await query.edit_message_text("❌ Ошибка при загрузке расходов.")

    async def _send_income_charts(self, query, account_ids: List[str], period: str, period_name: str, income_text: str):
        try:
            client = await self.bot.get_tinkoff_client(query.from_user.id)
            if not client:
                return
                
            income_chart = await client.generate_income_chart(account_ids, period)
            
            if income_chart:
                await query.message.reply_photo(
                    photo=income_chart,
                    caption=f"📊 График доходности за {period_name}",
                    parse_mode='Markdown'
                )
            else:
                await query.message.reply_text("❌ Не удалось построить график доходности")
            
            capital_chart = await client.generate_capital_chart(account_ids, period)
            
            if capital_chart:
                await query.message.reply_photo(
                    photo=capital_chart,
                    caption=f"📈 График изменения капитала за {period_name}",
                    parse_mode='Markdown'
                )
            else:
                await query.message.reply_text("❌ Не удалось построить график капитала")
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="income_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(income_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logging.error(f"Error sending charts: {e}")
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="income_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(income_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def _send_total_growth_chart(self, query, account_ids: List[str], growth_text: str):
        try:
            client = await self.bot.get_tinkoff_client(query.from_user.id)
            if not client:
                return
                
            growth_chart = await client.generate_total_growth_chart(account_ids)
            
            if growth_chart:
                await query.message.reply_photo(
                    photo=growth_chart,
                    caption="🚀 График общего роста капитала за все время",
                    parse_mode='Markdown'
                )
            else:
                await query.message.reply_text("❌ Не удалось построить график общего роста")
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(growth_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logging.error(f"Error sending total growth chart: {e}")
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(growth_text, reply_markup=reply_markup, parse_mode='Markdown')
            