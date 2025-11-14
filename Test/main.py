import os
import logging
import asyncio
from telegram import Update, Bot, MenuButtonWebApp, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.request import HTTPXRequest

from config import Config
from admin_manager import AdminManager
from user_service import UserService

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.admin_manager = AdminManager()
        self.user_service = UserService()
        
        request = HTTPXRequest(
            connect_timeout=30.0,
            read_timeout=30.0,
            write_timeout=30.0,
            pool_timeout=30.0
        )
        
        self.application = Application.builder().token(self.token).request(request).build()
        self.setup_handlers()

    def setup_handlers(self):
        """Настройка обработчиков"""
        # Команды для всех пользователей
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("support", self.support_command))
        
        # Команды для админов
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        self.application.add_handler(CommandHandler("broadcast", self.broadcast_command))
        self.application.add_handler(CommandHandler("messages", self.messages_command))
        self.application.add_handler(CommandHandler("reply", self.reply_command))
        
        # Обработка текстовых сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

    async def setup_menu_button(self):
        """Настройка кнопки меню для Mini App"""
        try:
            bot = Bot(self.token)
            # Для локального тестирования используем localhost
            web_app_url = "http://localhost:8080"
            
            menu_button = MenuButtonWebApp(
                text="📊 Investment App",
                web_app=WebAppInfo(url=web_app_url)
            )
            
            await bot.set_chat_menu_button(menu_button=menu_button)
            logger.info("Menu button setup successfully")
        except Exception as e:
            logger.error(f"Error setting up menu button: {e}")

    async def post_init(self, application):
        """Выполняется после инициализации приложения"""
        await self.setup_menu_button()

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /start"""
        user_id = update.effective_user.id
        
        text = (
            "👋 Добро пожаловать в Tinkoff Investments Bot!\n\n"
            "💼 *Основные функции:*\n"
            "• 📊 **Mini App** - полный анализ портфеля (откройте через кнопку меню)\n"
            "• 💬 **Поддержка** - связь с администраторами\n"
            "• 🔔 **Уведомления** - важные оповещения\n\n"
            "⚡ *Как начать:*\n"
            "1. Откройте **Mini App** через кнопку меню 📊\n"
            "2. Настройте API токен Tinkoff\n"
            "3. Выберите счета для отслеживания\n"
            "4. Анализируйте свои инвестиции!\n\n"
            "💬 *Нужна помощь?*\n"
            "Напишите сообщение - админы ответят вам лично!"
        )
        
        await update.message.reply_text(text, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /help"""
        help_text = (
            "📖 *Помощь по боту*\n\n"
            "👤 *Для пользователей:*\n"
            "/start - Начало работы\n"
            "/help - Эта справка\n"
            "/support - Связаться с поддержкой\n\n"
            "📊 *Mini App:*\n"
            "Откройте через кнопку меню 📊 для полного анализа портфеля\n\n"
            "💬 *Обратная связь:*\n"
            "Просто напишите сообщение - админы его увидят и ответят!\n\n"
            "👨‍💼 *Для админов:*\n"
            "/admin - Панель админа\n"
            "/broadcast - Рассылка\n"
            "/messages - Неотвеченные сообщения\n"
            "/reply - Ответ пользователю"
        )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def support_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /support"""
        support_text = (
            "💬 *Поддержка*\n\n"
            "Если у вас есть вопросы или проблемы:\n\n"
            "1. 📝 **Опишите проблему** в сообщении\n"
            "2. 🕒 **Укажите детали** (что произошло, когда)\n"
            "3. 📱 **Сообщите** используете ли вы Mini App\n\n"
            "Администраторы ответят вам в ближайшее время!\n\n"
            "⚡ *Быстрая помощь:*\n"
            "• Проблемы с API токеном - проверьте его в личном кабинете Tinkoff\n"
            "• Не загружаются данные - проверьте интернет-соединение\n"
            "• Ошибки в Mini App - перезагрузите приложение"
        )
        
        await update.message.reply_text(support_text, parse_mode='Markdown')

    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /admin - панель админа"""
        user_id = update.effective_user.id
        
        if not self.admin_manager.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав админа.")
            return
            
        # Получаем статистику
        user_files = os.listdir("user_data")
        user_count = len([f for f in user_files if f.startswith("user_") and f.endswith(".json")])
        unanswered_count = len(self.admin_manager.get_unanswered_messages())
        
        admin_text = (
            "👨‍💼 *Панель администратора*\n\n"
            "📊 *Статистика:*\n"
            f"• Пользователей: {user_count}\n"
            f"• Неотвеченных сообщений: {unanswered_count}\n"
            f"• Админов: {len(self.admin_manager.get_admins())}\n\n"
            "🛠 *Команды:*\n"
            "/broadcast - Рассылка сообщения\n"
            "/messages - Просмотр сообщений\n"
            "/reply - Ответ пользователю\n\n"
            "💡 *Быстрые действия:*\n"
            "• Ответьте на сообщение пользователя командой /reply\n"
            "• Сделайте объявление командой /broadcast\n"
            "• Проверьте новые сообщения командой /messages"
        )
        
        await update.message.reply_text(admin_text, parse_mode='Markdown')

    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /broadcast - рассылка"""
        user_id = update.effective_user.id
        
        if not self.admin_manager.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав админа.")
            return
            
        if not context.args:
            await update.message.reply_text(
                "❌ *Использование:* /broadcast [сообщение]\n\n"
                "Пример:\n"
                "/broadcast Важное обновление! Добавлены новые графики анализа.",
                parse_mode='Markdown'
            )
            return
            
        message = ' '.join(context.args)
        
        # Получаем всех пользователей из user_data
        user_files = os.listdir("user_data")
        user_ids = []
        
        for user_file in user_files:
            if user_file.startswith("user_") and user_file.endswith(".json"):
                try:
                    user_id = int(user_file[5:-5])  # Извлекаем ID из имени файла
                    user_ids.append(user_id)
                except ValueError:
                    continue
        
        # Отправляем сообщение всем пользователям
        success_count = 0
        fail_count = 0
        
        for user_id in user_ids:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📢 *Объявление от администратора:*\n\n{message}",
                    parse_mode='Markdown'
                )
                success_count += 1
                await asyncio.sleep(0.1)  # Задержка чтобы не превысить лимиты
            except Exception as e:
                logger.error(f"Error sending broadcast to {user_id}: {e}")
                fail_count += 1
        
        await update.message.reply_text(
            f"✅ *Рассылка завершена!*\n\n"
            f"• Успешно: {success_count}\n"
            f"• Не удалось: {fail_count}\n"
            f"• Всего: {len(user_ids)}",
            parse_mode='Markdown'
        )

    async def messages_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /messages - просмотр сообщений"""
        user_id = update.effective_user.id
        
        if not self.admin_manager.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав админа.")
            return
            
        unanswered = self.admin_manager.get_unanswered_messages()
        
        if not unanswered:
            await update.message.reply_text("✅ Нет неотвеченных сообщений.")
            return
            
        # Если много сообщений, разбиваем на несколько
        messages_text = "📨 *Неотвеченные сообщения:*\n\n"
        message_count = 0
        
        for target_user_id, data in list(unanswered.items())[:10]:  # Ограничиваем первые 10
            username = data['username']
            messages_text += f"👤 *{username}* (ID: `{target_user_id}`):\n"
            
            for i, msg in enumerate(data['messages'][:3]):  # Ограничиваем 3 сообщения на пользователя
                messages_text += f"{i+1}. {msg['text']}\n"
            
            messages_text += f"💬 Ответить: /reply {target_user_id} [сообщение]\n\n"
            message_count += 1
        
        if len(unanswered) > 10:
            messages_text += f"📋 ... и еще {len(unanswered) - 10} пользователей с сообщениями"
        
        await update.message.reply_text(messages_text, parse_mode='Markdown')

    async def reply_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Команда /reply - ответ пользователю"""
        user_id = update.effective_user.id
        
        if not self.admin_manager.is_admin(user_id):
            await update.message.reply_text("❌ У вас нет прав админа.")
            return
            
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ *Использование:* /reply [user_id] [сообщение]\n\n"
                "Пример:\n"
                "/reply 123456789 Здравствуйте! Мы получили ваше сообщение.",
                parse_mode='Markdown'
            )
            return
            
        try:
            target_user_id = int(context.args[0])
            reply_message = ' '.join(context.args[1:])
            
            # Отправка сообщения пользователю
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=f"💬 *Ответ от поддержки:*\n\n{reply_message}\n\n"
                         f"_Если у вас остались вопросы, просто напишите нам снова!_",
                    parse_mode='Markdown'
                )
                
                # Помечаем все сообщения пользователя как отвеченные
                if target_user_id in self.admin_manager.user_messages:
                    for i in range(len(self.admin_manager.user_messages[target_user_id]['messages'])):
                        self.admin_manager.mark_message_answered(target_user_id, i)
                
                await update.message.reply_text(
                    f"✅ *Ответ отправлен пользователю!*\n\n"
                    f"• ID пользователя: `{target_user_id}`\n"
                    f"• Сообщение: {reply_message}",
                    parse_mode='Markdown'
                )
                
            except Exception as e:
                error_msg = str(e)
                if "chat not found" in error_msg.lower():
                    await update.message.reply_text(
                        f"❌ Не удалось отправить сообщение пользователю `{target_user_id}`.\n"
                        f"Возможно, пользователь заблокировал бота или никогда не запускал его.",
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(f"❌ Ошибка отправки: {error_msg}")
                
        except ValueError:
            await update.message.reply_text("❌ Неверный user_id. Должен быть числом.")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка обычных сообщений"""
        user_id = update.effective_user.id
        username = update.effective_user.username or "Без username"
        message_text = update.message.text
        
        # Если это админ - игнорируем обычные сообщения
        if self.admin_manager.is_admin(user_id):
            await update.message.reply_text(
                "ℹ️ Вы админ. Используйте /admin для доступа к админским функциям.\n\n"
                "💡 *Подсказка:* Вы можете ответить пользователю командой /reply",
                parse_mode='Markdown'
            )
            return
            
        # Сохраняем сообщение пользователя
        self.admin_manager.add_user_message(user_id, username, message_text)
        
        # Уведомляем админов
        admins = self.admin_manager.get_admins()
        notified_admins = 0
        
        for admin_id in admins:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"📨 *Новое сообщение от пользователя:*\n\n"
                         f"👤 *{username}* (ID: `{user_id}`)\n"
                         f"💬 {message_text}\n\n"
                         f"💬 Ответить: /reply {user_id} [ваш ответ]",
                    parse_mode='Markdown'
                )
                notified_admins += 1
            except Exception as e:
                logger.error(f"Error notifying admin {admin_id}: {e}")
        
        # Подтверждаем пользователю
        if notified_admins > 0:
            await update.message.reply_text(
                "✅ Ваше сообщение отправлено администраторам! "
                "Мы ответим вам в ближайшее время.\n\n"
                "💡 *Совет:* Откройте Mini App через кнопку меню для анализа ваших инвестиций!",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "⚠️ К сожалению, в данный момент нет доступных администраторов. "
                "Попробуйте позже или откройте Mini App для самостоятельного анализа.",
                parse_mode='Markdown'
            )

    def run(self):
        """Запуск бота"""
        print("🤖 Бот запущен!")
        print("⚡ Бот настроен для:")
        print("   - Mini App через кнопку меню")
        print("   - Поддержки пользователей") 
        print("   - Админских функций")
        
        # Настраиваем меню кнопку перед запуском
        asyncio.run(self.setup_menu_button())
        
        # Запускаем бота
        self.application.run_polling(drop_pending_updates=True)

def main():
    """Основная функция"""
    try:
        Config.validate()
        print("✅ Конфигурация загружена успешно")
        
        # Запуск бота
        bot = TelegramBot()
        bot.run()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        logger.error(f"Main error: {e}")

if __name__ == "__main__":
    main()
    