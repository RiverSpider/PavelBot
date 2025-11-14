import logging
from typing import List, Dict
from decimal import Decimal
from tinkoff.invest import AsyncClient, PortfolioPosition
from tinkoff.invest.utils import quotation_to_decimal

logger = logging.getLogger(__name__)

class PortfolioService:
    def __init__(self, token: str):
        self.token = token

    async def get_portfolio_positions(self, account_id: str) -> List[PortfolioPosition]:
        """Получение позиций портфеля"""
        try:
            async with AsyncClient(self.token) as client:
                portfolio = await client.operations.get_portfolio(account_id=account_id)
                return portfolio.positions
        except Exception as e:
            logger.error(f"Error getting portfolio for account {account_id}: {e}")
            return []

    async def get_portfolio_summary(self, account_id: str, instrument_service) -> Dict:
        """Получение сводной информации по портфелю"""
        try:
            positions = await self.get_portfolio_positions(account_id)
            
            total_portfolio_value = Decimal('0')
            positions_info = []
            stocks = []
            bonds = []
            etfs = []
            currencies = []

            for position in positions:
                try:
                    current_price = quotation_to_decimal(position.current_price)
                    quantity = quotation_to_decimal(position.quantity)
                    expected_yield = quotation_to_decimal(position.expected_yield)
                    position_value = current_price * quantity
                    
                    total_portfolio_value += position_value
                    
                    instrument_name = await instrument_service.get_instrument_name(position.figi)
                    
                    position_info = {
                        'name': instrument_name,
                        'figi': position.figi,
                        'quantity': float(quantity),
                        'current_price': float(current_price),
                        'value': float(position_value),
                        'yield': float(expected_yield),
                        'type': position.instrument_type
                    }
                    
                    positions_info.append(position_info)
                    
                    instrument_type = str(position.instrument_type).lower()
                    if 'share' in instrument_type or 'акция' in instrument_name.lower():
                        stocks.append(position_info)
                    elif 'bond' in instrument_type or 'облигация' in instrument_name.lower():
                        bonds.append(position_info)
                    elif 'etf' in instrument_type or 'фонд' in instrument_name.lower():
                        etfs.append(position_info)
                    elif 'currency' in instrument_type:
                        currencies.append(position_info)
                        
                except Exception as e:
                    logger.warning(f"Error processing position {position.figi}: {e}")
                    continue

            return {
                'total_value': float(total_portfolio_value),
                'positions': positions_info,
                'stocks': stocks,
                'bonds': bonds,
                'etfs': etfs,
                'currencies': currencies
            }
        except Exception as e:
            logger.error(f"Error getting portfolio summary for account {account_id}: {e}")
            return {
                'total_value': 0.0,
                'positions': [],
                'stocks': [],
                'bonds': [],
                'etfs': [],
                'currencies': []
            }
        