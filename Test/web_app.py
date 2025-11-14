import logging
import base64
import io
import os
from aiohttp import web
import aiohttp_jinja2
import jinja2
from pathlib import Path

from config import Config
from user_service import UserService
from tinkoff_client import TinkoffInvestmentsClient

logger = logging.getLogger(__name__)

class WebApp:
    def __init__(self):
        self.app = web.Application()
        self.user_service = UserService()
        
        # Настройка шаблонов с абсолютным путем
        current_dir = Path(__file__).parent
        templates_dir = current_dir / 'templates'
        
        aiohttp_jinja2.setup(
            self.app, 
            loader=jinja2.FileSystemLoader(str(templates_dir))
        )
        
        self.setup_routes()
        
    def setup_routes(self):
        """Настройка маршрутов"""
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/api/accounts', self.get_accounts)
        self.app.router.add_get('/api/portfolio', self.get_portfolio)
        self.app.router.add_get('/api/income', self.get_income)
        self.app.router.add_get('/api/chart/capital', self.get_capital_chart)
        self.app.router.add_get('/api/chart/income', self.get_income_chart)
        self.app.router.add_post('/api/set_token', self.set_token)
        self.app.router.add_post('/api/set_accounts', self.set_accounts)
        
    @aiohttp_jinja2.template('index.html')
    async def index(self, request):
        """Главная страница Mini App"""
        return {}
    
    async def get_accounts(self, request):
        """Получение списка счетов"""
        try:
            user_id = int(request.query.get('user_id', '0'))
            token = await self.user_service.get_user_api_token(user_id)
            
            if not token:
                # Для тестирования используем токен из конфига
                token = Config.TINKOFF_API_TOKEN
                if not token:
                    return web.json_response({'error': 'Token not set'}, status=400)
                
            client = TinkoffInvestmentsClient(token)
            accounts = await client.get_accounts()
            
            return web.json_response({'accounts': accounts})
            
        except Exception as e:
            logger.error(f"Error getting accounts: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_portfolio(self, request):
        """Получение портфеля"""
        try:
            user_id = int(request.query.get('user_id', '0'))
            token = await self.user_service.get_user_api_token(user_id)
            
            if not token:
                token = Config.TINKOFF_API_TOKEN
                if not token:
                    return web.json_response({'error': 'Token not set'}, status=400)
                
            account_ids = await self.user_service.get_user_accounts(user_id)
            if not account_ids:
                # Для тестирования используем первый доступный счет
                client = TinkoffInvestmentsClient(token)
                accounts = await client.get_accounts()
                if accounts:
                    account_ids = [accounts[0]['id']]
                else:
                    return web.json_response({'error': 'No accounts available'}, status=400)
                
            client = TinkoffInvestmentsClient(token)
            portfolio = await client.get_portfolio_summary(account_ids)
            
            return web.json_response(portfolio)
            
        except Exception as e:
            logger.error(f"Error getting portfolio: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_income(self, request):
        """Получение доходности"""
        try:
            user_id = int(request.query.get('user_id', '0'))
            period = request.query.get('period', 'week')
            token = await self.user_service.get_user_api_token(user_id)
            
            if not token:
                token = Config.TINKOFF_API_TOKEN
                if not token:
                    return web.json_response({'error': 'Token not set'}, status=400)
                
            account_ids = await self.user_service.get_user_accounts(user_id)
            if not account_ids:
                client = TinkoffInvestmentsClient(token)
                accounts = await client.get_accounts()
                if accounts:
                    account_ids = [accounts[0]['id']]
                else:
                    return web.json_response({'error': 'No accounts selected'}, status=400)
                
            client = TinkoffInvestmentsClient(token)
            income_data = await client.calculate_income(account_ids, period)
            
            # Конвертируем Decimal в float для JSON
            income_data = {k: float(v) if hasattr(v, '__float__') else v 
                         for k, v in income_data.items()}
            
            return web.json_response(income_data)
            
        except Exception as e:
            logger.error(f"Error getting income: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_capital_chart(self, request):
        """Получение графика капитала"""
        try:
            user_id = int(request.query.get('user_id', '0'))
            period = request.query.get('period', 'week')
            token = await self.user_service.get_user_api_token(user_id)
            
            if not token:
                token = Config.TINKOFF_API_TOKEN
                if not token:
                    return web.json_response({'error': 'Token not set'}, status=400)
                
            account_ids = await self.user_service.get_user_accounts(user_id)
            if not account_ids:
                client = TinkoffInvestmentsClient(token)
                accounts = await client.get_accounts()
                if accounts:
                    account_ids = [accounts[0]['id']]
                else:
                    return web.json_response({'error': 'No accounts selected'}, status=400)
                
            client = TinkoffInvestmentsClient(token)
            chart = await client.generate_capital_chart(account_ids, period)
            
            if chart:
                chart_data = base64.b64encode(chart.getvalue()).decode()
                return web.json_response({'chart': chart_data})
            else:
                return web.json_response({'error': 'Failed to generate chart'}, status=500)
                
        except Exception as e:
            logger.error(f"Error getting capital chart: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def get_income_chart(self, request):
        """Получение графика доходности"""
        try:
            user_id = int(request.query.get('user_id', '0'))
            period = request.query.get('period', 'week')
            token = await self.user_service.get_user_api_token(user_id)
            
            if not token:
                token = Config.TINKOFF_API_TOKEN
                if not token:
                    return web.json_response({'error': 'Token not set'}, status=400)
                
            account_ids = await self.user_service.get_user_accounts(user_id)
            if not account_ids:
                client = TinkoffInvestmentsClient(token)
                accounts = await client.get_accounts()
                if accounts:
                    account_ids = [accounts[0]['id']]
                else:
                    return web.json_response({'error': 'No accounts selected'}, status=400)
                
            client = TinkoffInvestmentsClient(token)
            chart = await client.generate_income_chart(account_ids, period)
            
            if chart:
                chart_data = base64.b64encode(chart.getvalue()).decode()
                return web.json_response({'chart': chart_data})
            else:
                return web.json_response({'error': 'Failed to generate chart'}, status=500)
                
        except Exception as e:
            logger.error(f"Error getting income chart: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def set_token(self, request):
        """Установка API токена"""
        try:
            data = await request.json()
            user_id = int(data.get('user_id', '0'))
            token = data['token']
            
            await self.user_service.set_user_api_token(user_id, token)
            
            # Проверяем токен
            client = TinkoffInvestmentsClient(token)
            is_valid = await client.validate_token()
            
            return web.json_response({'valid': is_valid})
            
        except Exception as e:
            logger.error(f"Error setting token: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    async def set_accounts(self, request):
        """Установка выбранных счетов"""
        try:
            data = await request.json()
            user_id = int(data.get('user_id', '0'))
            account_ids = data['account_ids']
            
            await self.user_service.set_user_accounts(user_id, account_ids)
            
            return web.json_response({'success': True})
            
        except Exception as e:
            logger.error(f"Error setting accounts: {e}")
            return web.json_response({'error': str(e)}, status=500)
    
    def run(self, host='localhost', port=8080):
        """Запуск веб-приложения"""
        web.run_app(self.app, host=host, port=port)
        