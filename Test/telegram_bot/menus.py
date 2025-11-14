import logging
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import NetworkError, TimedOut

logger = logging.getLogger(__name__)

class MenuManager:
    def __init__(self, bot):
        self.bot = bot

    async def safe_edit_message(self, query, text: str, **kwargs):
        """Безопасное редактирование сообщения с повторными попытками"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await query.edit_message_text(text, **kwargs)
                return True
            except (NetworkError, TimedOut) as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"Failed to edit message after {max_retries} attempts")
                    return False
            except Exception as e:
                logger.error(f"Unexpected error while editing message: {e}")
                return False
        return False

    async def safe_send_message(self, message, text: str, **kwargs):
        """Безопасная отправка сообщения с повторными попытками"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await message.reply_text(text, **kwargs)
                return True
            except (NetworkError, TimedOut) as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"Failed to send message after {max_retries} attempts")
                    return False
            except Exception as e:
                logger.error(f"Unexpected error while sending message: {e}")
                return False
        return False

    async def show_token_setup(self, message):
        """Показать настройку токена"""
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            "🔑 *Настройка API токена Tinkoff*\n\n"
            "Для работы с ботом необходим API токен Tinkoff Invest.\n\n"
            "1. Получите токен в личном кабинете Tinkoff Invest\n"
            "2. Отправьте его мне сообщением\n\n"
            "⚠️ *Внимание:* Токен хранится в зашифрованном виде и не передается третьим лицам.\n\n"
            "Отправьте ваш API токен:"
        )
        
        await self.safe_send_message(message, text, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_accounts(self, message):
        try:
            user_id = message.from_user.id
            client = await self.bot.get_tinkoff_client(user_id)
            
            if not client:
                await self.show_token_setup(message)
                return
            
            await self.safe_send_message(message, "⏳ Получаю список ваших счетов...")
            
            accounts = await client.get_accounts()
            
            if not accounts:
                await self.safe_send_message(
                    message,
                    "❌ Не удалось получить список счетов.\n"
                    "Проверьте:\n"
                    "• Корректность Tinkoff API токена\n"
                    "• Наличие открытых счетов\n"
                    "• Доступ к интернету"
                )
                return
            
            # Получаем текущие выбранные счета
            selected_accounts = await self.bot.user_service.get_user_accounts(user_id)
            
            text = "📋 *Ваши счета в Tinkoff:*\n\n"
            keyboard = []
            
            for i, account in enumerate(accounts, 1):
                emoji = client.get_account_emoji(account['name'])
                is_selected = account['id'] in selected_accounts
                status_emoji = "✅" if is_selected else "❌"
                
                account_name_escaped = self.bot.escape_markdown(account['name'])
                account_type_escaped = self.bot.escape_markdown(account['type'])
                account_id_escaped = self.bot.escape_markdown(account['id'])
                
                text += f"{emoji} *Счет {i}:*\n"
                text += f"🏷️ *Название:* {account_name_escaped}\n"
                text += f"📊 *Тип:* {account_type_escaped}\n"
                text += f"📈 *Стоимость:* {account['portfolio_value']:,.2f} ₽\n"
                text += f"🔐 *ID:* `{account_id_escaped}`\n"
                text += f"📌 *Статус:* {status_emoji}\n\n"
                
                if is_selected:
                    keyboard.append([InlineKeyboardButton(
                        f"❌ Убрать {account['name']}",
                        callback_data=f"toggle_account_{account['id']}"
                    )])
                else:
                    keyboard.append([InlineKeyboardButton(
                        f"✅ Добавить {account['name']}",
                        callback_data=f"toggle_account_{account['id']}"
                    )])
            
            keyboard.append([InlineKeyboardButton("💾 Сохранить выбор", callback_data="save_accounts")])
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
            
            text += "👇 Выберите счета для работы (можно несколько):"
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await self.safe_send_message(message, text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logging.error(f"Error in show_accounts: {e}")
            await self.safe_send_message(message, "❌ Ошибка при получении списка счетов.")

    async def show_accounts_query(self, query):
        try:
            user_id = query.from_user.id
            client = await self.bot.get_tinkoff_client(user_id)
            
            if not client:
                await self.safe_edit_message(query, "❌ API токен не установлен. Используйте /set_token")
                return
            
            await self.safe_edit_message(query, "⏳ Получаю список ваших счетов...")
            
            accounts = await client.get_accounts()
            
            if not accounts:
                await self.safe_edit_message(query, "❌ Не удалось получить список счетов.")
                return
            
            # Получаем текущие выбранные счета
            selected_accounts = await self.bot.user_service.get_user_accounts(user_id)
            
            text = "📋 *Ваши счета в Tinkoff:*\n\n"
            keyboard = []
            
            for i, account in enumerate(accounts, 1):
                emoji = client.get_account_emoji(account['name'])
                is_selected = account['id'] in selected_accounts
                status_emoji = "✅" if is_selected else "❌"
                
                account_name_escaped = self.bot.escape_markdown(account['name'])
                
                text += f"{emoji} *Счет {i}:*\n"
                text += f"🏷️ *Название:* {account_name_escaped}\n"
                text += f"📈 *Стоимость:* {account['portfolio_value']:,.2f} ₽\n"
                text += f"📌 *Статус:* {status_emoji}\n\n"
                
                if is_selected:
                    keyboard.append([InlineKeyboardButton(
                        f"❌ Убрать {account['name']}",
                        callback_data=f"toggle_account_{account['id']}"
                    )])
                else:
                    keyboard.append([InlineKeyboardButton(
                        f"✅ Добавить {account['name']}",
                        callback_data=f"toggle_account_{account['id']}"
                    )])
            
            keyboard.append([InlineKeyboardButton("💾 Сохранить выбор", callback_data="save_accounts")])
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
            
            text += "👇 Выберите счета для работы (можно несколько):"
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await self.safe_edit_message(query, text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logging.error(f"Error in show_accounts_query: {e}")
            await self.safe_edit_message(query, "❌ Ошибка при получении списка счетов.")

    async def show_main_menu(self, message):
        user_id = message.from_user.id
        selected_accounts = await self.bot.user_service.get_user_accounts(user_id)
        accounts_count = len(selected_accounts)
        
        keyboard = [
            [
                InlineKeyboardButton("👤 Мой портфель", callback_data="portfolio"),
                InlineKeyboardButton("💰 Доходность", callback_data="income_menu")
            ],
            [
                InlineKeyboardButton("📊 Все позиции", callback_data="positions"),
                InlineKeyboardButton("🎯 Доход от облигаций", callback_data="bond_income")
            ],
            [
                InlineKeyboardButton("📋 История операций", callback_data="operations"),
                InlineKeyboardButton("💸 Расходы", callback_data="expenses")
            ],
            [
                InlineKeyboardButton("🚀 Общий рост", callback_data="total_growth"),
                InlineKeyboardButton("🔄 Сменить счета", callback_data="change_account")
            ],
            [
                InlineKeyboardButton("🔑 Управление API", callback_data="manage_token"),
                InlineKeyboardButton("🔔 Тест уведомлений", callback_data="notifications_menu")
            ],
            [
                InlineKeyboardButton("ℹ️ Помощь", callback_data="help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"🏠 *Главное меню* 🏠\n\n"
        text += f"📊 Выбрано счетов: {accounts_count}\n"
        text += f"Выберите действие:"
        
        await self.safe_send_message(
            message,
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def show_main_menu_query(self, query):
        user_id = query.from_user.id
        selected_accounts = await self.bot.user_service.get_user_accounts(user_id)
        accounts_count = len(selected_accounts)
        
        keyboard = [
            [
                InlineKeyboardButton("👤 Мой портфель", callback_data="portfolio"),
                InlineKeyboardButton("💰 Доходность", callback_data="income_menu")
            ],
            [
                InlineKeyboardButton("📊 Все позиции", callback_data="positions"),
                InlineKeyboardButton("🎯 Доход от облигаций", callback_data="bond_income")
            ],
            [
                InlineKeyboardButton("📋 История операций", callback_data="operations"),
                InlineKeyboardButton("💸 Расходы", callback_data="expenses")
            ],
            [
                InlineKeyboardButton("🚀 Общий рост", callback_data="total_growth"),
                InlineKeyboardButton("🔄 Сменить счета", callback_data="change_account")
            ],
            [
                InlineKeyboardButton("🔑 Управление API", callback_data="manage_token"),
                InlineKeyboardButton("🔔 Тест уведомлений", callback_data="notifications_menu")
            ],
            [
                InlineKeyboardButton("ℹ️ Помощь", callback_data="help")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = f"🏠 *Главное меню* 🏠\n\n"
        text += f"📊 Выбрано счетов: {accounts_count}\n"
        text += f"Выберите действие:"
        
        await self.safe_edit_message(
            query,
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def show_token_management(self, query):
        """Показать меню управления API токеном"""
        user_id = query.from_user.id
        has_token = await self.bot.user_service.get_user_api_token(user_id) is not None
        
        keyboard = []
        
        if has_token:
            keyboard.append([InlineKeyboardButton("🗑️ Удалить API токен", callback_data="delete_token_confirm")])
        else:
            keyboard.append([InlineKeyboardButton("🔑 Установить API токен", callback_data="set_token")])
        
        keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="main_menu")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = "🔑 *Управление API токеном*\n\n"
        
        if has_token:
            text += "✅ API токен установлен\n\n"
            text += "Вы можете удалить токен, если хотите использовать другой аккаунт или прекратить работу с ботом."
        else:
            text += "❌ API токен не установлен\n\n"
            text += "Для работы с ботом необходимо установить API токен Tinkoff Invest."
        
        await self.safe_edit_message(query, text, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_delete_token_confirmation(self, query):
        """Показать подтверждение удаления токена"""
        keyboard = [
            [
                InlineKeyboardButton("✅ Да, удалить", callback_data="delete_token"),
                InlineKeyboardButton("❌ Нет, отмена", callback_data="manage_token")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            "⚠️ *Подтверждение удаления API токена*\n\n"
            "Вы уверены, что хотите удалить ваш API токен?\n\n"
            "Это действие приведет к:\n"
            "• Удалению вашего API токена\n"
            "• Удалению выбранных счетов\n"
            "• Очистке всех персональных данных\n\n"
            "После удаления вы сможете установить новый токен."
        )
        
        await self.safe_edit_message(query, text, reply_markup=reply_markup, parse_mode='Markdown')

    async def show_help(self, query):
        try:
            help_text = """
📖 Помощь по боту инвестиций 📖

*Основные функции:*
• 👤 *Портфель* - общая стоимость и основные позиции
• 📊 *Все позиции* - полный список с пагинацией
• 💰 *Доходность* - анализ доходности за разные периоды с графиками
• 🚀 *Общий рост* - доход за все время с графиками
• 🎯 *Облигации* - доход от купонных выплат
• 📋 *Операции* - история всех операций с деталями
• 💸 *Расходы* - комиссии и прочие расходы

*Новые возможности:*
• 📈 *Графики капитала* - визуализация изменения стоимости портфеля
• 📊 *Графики доходности* - наглядное представление доходов и расходов
• 🚀 *Общий рост за все время* - полная история инвестиций
• 🔑 *Безопасное хранение* - API ключи хранятся в зашифрованном виде
• 📊 *Множественные счета* - работа с несколькими счетами одновременно

💡 *Для начала работы просто выберите нужный пункт из меню!*
            """
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self.safe_edit_message(query, help_text, reply_markup=reply_markup, parse_mode='Markdown')
        except Exception as e:
            logging.error(f"Error in show_help: {e}")
            await self.safe_edit_message(query, "❌ Ошибка при отображении справки.")
            