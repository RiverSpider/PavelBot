import logging
from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime, timedelta
import asyncio
import httpx
from tinkoff.invest import AsyncClient

from config import Config
from Test.services.account_service import AccountService
from services.portfolio_service import PortfolioService
from services.operation_service import OperationService
from services.instrument_service import InstrumentService
from services.chart_service import ChartService

logger = logging.getLogger(__name__)

class TinkoffInvestmentsClient:
    def __init__(self, api_token: str):
        self.token = api_token
        self.logger = logger

        self.account_service = AccountService(self.token)
        self.portfolio_service = PortfolioService(self.token)
        self.operation_service = OperationService(self.token)
        self.instrument_service = InstrumentService(self.token)
        self.chart_service = ChartService(self.token)

    async def validate_token(self) -> bool:
        """Проверка валидности API токена"""
        try:
            async with AsyncClient(self.token) as client:
                await client.users.get_accounts()
                return True
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return False

    async def get_accounts(self) -> List[Dict]:
        """Получение списка всех счетов пользователя"""
        try:
            return await self.account_service.get_all_accounts()
        except httpx.ReadError as e:
            logger.error(f"Network error while getting accounts: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting accounts: {e}")
            return []

    async def validate_account(self, account_id: str) -> bool:
        """Проверка валидности счета"""
        try:
            return await self.account_service.validate_account(account_id)
        except Exception as e:
            logger.error(f"Error validating account {account_id}: {e}")
            return False

    def get_account_emoji(self, account_name: str) -> str:
        """Получить emoji для типа счета"""
        return self.account_service.get_account_emoji(account_name)

    async def get_portfolio_summary(self, account_ids: List[str]) -> Dict:
        """Получение сводной информации по портфелю для нескольких счетов"""
        try:
            tasks = []
            for account_id in account_ids:
                task = self.portfolio_service.get_portfolio_summary(account_id, self.instrument_service)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            total_value = 0.0
            all_positions = []
            stocks = []
            bonds = []
            etfs = []
            currencies = []
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error getting portfolio: {result}")
                    continue
                    
                total_value += result['total_value']
                all_positions.extend(result['positions'])
                stocks.extend(result['stocks'])
                bonds.extend(result['bonds'])
                etfs.extend(result['etfs'])
                currencies.extend(result['currencies'])
            
            return {
                'total_value': total_value,
                'positions': all_positions,
                'stocks': stocks,
                'bonds': bonds,
                'etfs': etfs,
                'currencies': currencies
            }
        except httpx.ReadError as e:
            logger.error(f"Network error while getting portfolio: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}")
            return {
                'total_value': 0.0,
                'positions': [],
                'stocks': [],
                'bonds': [],
                'etfs': [],
                'currencies': []
            }

    async def calculate_income(self, account_ids: List[str], period: str) -> Dict[str, Decimal]:
        """Расчет дохода за указанный период для нескольких счетов"""
        try:
            return await self.operation_service.calculate_income_for_accounts(account_ids, period)
        except httpx.ReadError as e:
            logger.error(f"Network error while calculating income: {e}")
            raise
        except Exception as e:
            logger.error(f"Error calculating income: {e}")
            return {
                'total_income': Decimal('0'),
                'bond_income': Decimal('0'),
                'dividend_income': Decimal('0'),
                'commission_expenses': Decimal('0'),
                'period': period
            }

    async def calculate_total_capital_growth(self, account_ids: List[str]) -> Dict[str, Decimal]:
        """Расчет общего роста капитала за все время для нескольких счетов"""
        try:
            return await self.operation_service.calculate_total_capital_growth_for_accounts(account_ids)
        except httpx.ReadError as e:
            logger.error(f"Network error while calculating capital growth: {e}")
            raise
        except Exception as e:
            logger.error(f"Error calculating total capital growth: {e}")
            return {
                'total_growth': Decimal('0'),
                'total_invested': Decimal('0'),
                'total_withdrawn': Decimal('0'),
                'net_growth': Decimal('0')
            }

    async def generate_capital_chart(self, account_ids: List[str], period: str):
        """Генерация графика изменения капитала для нескольких счетов"""
        try:
            return await self.chart_service.generate_capital_chart(account_ids, period)
        except Exception as e:
            logger.error(f"Error generating capital chart: {e}")
            return None

    async def generate_income_chart(self, account_ids: List[str], period: str):
        """Генерация графика доходности для нескольких счетов"""
        try:
            return await self.chart_service.generate_income_chart(account_ids, period)
        except Exception as e:
            logger.error(f"Error generating income chart: {e}")
            return None

    def _operation_to_decimal(self, operation):
        """Конвертация операции в decimal"""
        return self.operation_service._operation_to_decimal(operation)
    