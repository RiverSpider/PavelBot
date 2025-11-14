import logging
from datetime import datetime, timedelta
from typing import List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

class PortfolioHandler:
    def __init__(self, bot):
        self.bot = bot

    async def show_portfolio(self, query):
        try:
            user_id = query.from_user.id
            selected_accounts = await self.bot.user_service.get_user_accounts(user_id)
            
            if not selected_accounts:
                await query.edit_message_text("❌ Счета не выбраны. Используйте /start для выбора счетов.")
                return
            
            client = await self.bot.get_tinkoff_client(user_id)
            if not client:
                await query.edit_message_text("❌ API токен не установлен. Используйте /set_token")
                return
                
            await query.edit_message_text("⏳ Загружаю данные портфеля...")
            portfolio_data = await client.get_portfolio_summary(selected_accounts)
            
            portfolio_text = "📊 *Ваш инвестиционный портфель*\n\n"
            portfolio_text += f"💰 *Общая стоимость:* {portfolio_data['total_value']:,.2f} ₽\n"
            portfolio_text += f"📊 *Количество счетов:* {len(selected_accounts)}\n\n"
            
            top_positions = sorted(portfolio_data['positions'], key=lambda x: x['value'], reverse=True)[:5]
            
            for i, pos in enumerate(top_positions, 1):
                emoji = self._get_position_emoji(pos)
                pos_name_escaped = self.bot.escape_markdown(pos['name'])
                portfolio_text += f"{i}. {emoji} *{pos_name_escaped}*\n"
                portfolio_text += f"   💰 Стоимость: {pos['value']:,.2f} ₽\n"
                portfolio_text += f"   📈 Доходность: {pos['yield']:,.2f} ₽\n\n"
            
            if len(portfolio_data['positions']) > 5:
                portfolio_text += f"📝 *Всего позиций:* {len(portfolio_data['positions'])}\n"
                portfolio_text += "👉 Нажмите *\"Все позиции\"* чтобы увидеть полный список"
                
            keyboard = [
                [InlineKeyboardButton("📊 Все позиции", callback_data="positions_page_0")],
                [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(portfolio_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logging.error(f"Error in show_portfolio: {e}")
            await query.edit_message_text("❌ Ошибка при загрузке портфеля.")

    async def show_positions_page(self, query, page=0):
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

            await query.edit_message_text("⏳ Загружаю детали по позициям...")
            
            portfolio_data = await client.get_portfolio_summary(selected_accounts)
            
            all_positions = portfolio_data['positions']
            all_positions.sort(key=lambda x: x['value'], reverse=True)
            
            page_size = 10
            total_pages = (len(all_positions) + page_size - 1) // page_size
            
            if page >= total_pages:
                page = total_pages - 1
            if page < 0:
                page = 0
                
            start_idx = page * page_size
            end_idx = min((page + 1) * page_size, len(all_positions))
            current_positions = all_positions[start_idx:end_idx]
            
            positions_text = f"📊 *Все позиции ({page + 1}/{total_pages})*\n\n"
            positions_text += f"*Всего позиций:* {len(all_positions)}\n"
            positions_text += f"*Количество счетов:* {len(selected_accounts)}\n\n"
            
            for i, pos in enumerate(current_positions, start=start_idx + 1):
                emoji = self._get_position_emoji(pos)
                pos_name_escaped = self.bot.escape_markdown(pos['name'])
                
                positions_text += f"{i}. {emoji} *{pos_name_escaped}*\n"
                positions_text += f"   📊 *Тип:* {pos['type']}\n"
                positions_text += f"   💰 *Стоимость:* {pos['value']:,.2f} ₽\n"
                positions_text += f"   📦 *Количество:* {pos['quantity']} шт.\n"
                positions_text += f"   💵 *Цена:* {pos['current_price']:,.2f} ₽\n"
                positions_text += f"   📈 *Доходность:* {pos['yield']:,.2f} ₽\n\n"
            
            keyboard = []
            
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"positions_page_{page-1}"))
            
            nav_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="no_action"))
            
            if page < total_pages - 1:
                nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"positions_page_{page+1}"))
            
            if nav_buttons:
                keyboard.append(nav_buttons)
            
            keyboard.append([InlineKeyboardButton("🔙 Назад в меню", callback_data="main_menu")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(positions_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logging.error(f"Error in show_positions_page: {e}")
            await query.edit_message_text("❌ Ошибка при загрузке позиций.")

    async def show_operations_page(self, query, page=0):
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

            await query.edit_message_text("⏳ Загружаю историю операций...")
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            operations = await client.get_operations(selected_accounts, start_date, end_date)
            
            if not operations:
                await query.edit_message_text("📭 Операций за последние 30 дней не найдено.")
                return
            
            operations.sort(key=lambda x: x.date, reverse=True)
            
            page_size = 10
            total_pages = (len(operations) + page_size - 1) // page_size
            
            if page >= total_pages:
                page = total_pages - 1
            if page < 0:
                page = 0
                
            start_idx = page * page_size
            end_idx = min((page + 1) * page_size, len(operations))
            current_operations = operations[start_idx:end_idx]
            
            operations_text = f"📋 *История операций ({page + 1}/{total_pages})*\n\n"
            operations_text += f"*Период:* последние 30 дней\n"
            operations_text += f"*Всего операций:* {len(operations)}\n"
            operations_text += f"*Количество счетов:* {len(selected_accounts)}\n\n"
            
            for i, operation in enumerate(current_operations, start=start_idx + 1):
                date_str = operation.date.strftime("%d.%m.%Y %H:%M")
                amount = float(client._operation_to_decimal(operation))
                
                operation_description = client.operation_service.get_operation_description(operation)
                instrument_name = await client.operation_service.get_operation_instrument_name(
                    operation, client.instrument_service
                )
                
                operation_type_emoji = self._get_operation_type_emoji(operation.operation_type)
                
                operations_text += f"{i}. {operation_type_emoji} *{date_str}*\n"
                operations_text += f"   *Операция:* {operation_description}\n"
                
                if instrument_name and instrument_name != "Неизвестный инструмент":
                    instrument_name_escaped = self.bot.escape_markdown(instrument_name)
                    operations_text += f"   *Инструмент:* {instrument_name_escaped}\n"
                
                if amount != 0:
                    amount_text = f"{amount:,.2f} ₽"
                    if amount > 0:
                        operations_text += f"   💰 *Зачислено:* {amount_text}\n"
                    else:
                        operations_text += f"   💸 *Списано:* {abs(amount):,.2f} ₽\n"
                
                operations_text += "\n"
            
            keyboard = []
            
            nav_buttons = []
            if page > 0:
                nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"operations_page_{page-1}"))
            
            nav_buttons.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="no_action"))
            
            if page < total_pages - 1:
                nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"operations_page_{page+1}"))
            
            if nav_buttons:
                keyboard.append(nav_buttons)
            
            keyboard.append([InlineKeyboardButton("🔙 Назад в меню", callback_data="main_menu")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(operations_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logging.error(f"Error in show_operations_page: {e}")
            await query.edit_message_text("❌ Ошибка при загрузке операций.")

    def _get_operation_type_emoji(self, operation_type) -> str:
        operation_type_str = str(operation_type)
        emoji_map = {
            "OPERATION_TYPE_BUY": "🟢",
            "OPERATION_TYPE_SELL": "🔴", 
            "OPERATION_TYPE_COUPON": "💰",
            "OPERATION_TYPE_DIVIDEND": "💵",
            "OPERATION_TYPE_BROKER_COMMISSION": "💸",
            "OPERATION_TYPE_SERVICE_COMMISSION": "⚖️",
            "OPERATION_TYPE_TAX": "🏛️",
            "OPERATION_TYPE_TAX_DIVIDEND": "🏛️",
            "OPERATION_TYPE_TAX_COUPON": "🏛️"
        }
        
        for key, emoji in emoji_map.items():
            if key in operation_type_str:
                return emoji
                
        return "📄"

    def _get_position_emoji(self, position) -> str:
        name_lower = position['name'].lower()
        type_lower = str(position['type']).lower()
        
        if 'акция' in name_lower or 'share' in type_lower:
            return "📈"
        elif 'облигация' in name_lower or 'bond' in type_lower:
            return "🎯"
        elif 'фонд' in name_lower or 'etf' in type_lower:
            return "📊"
        elif 'валюта' in name_lower or 'currency' in type_lower:
            return "💱"
        else:
            return "💼"
        