import logging
from web_app import WebApp

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def main():
    """Запуск Mini App"""
    print("🌐 Запуск Mini App...")
    web_app = WebApp()
    web_app.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    main()
    