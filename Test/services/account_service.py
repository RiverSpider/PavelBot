import logging
from typing import List, Dict
from tinkoff.invest import AsyncClient, AccountType, AccountStatus
from tinkoff.invest.utils import quotation_to_decimal

logger = logging.getLogger(__name__)

class AccountService:
    def __init__(self, token: str):
        self.token = token

    async def get_all_accounts(self) -> List[Dict]:
        """Получение списка всех счетов пользователя с информацией о портфеле"""
        try:
            logger.info("Getting accounts from Tinkoff API")
            async with AsyncClient(self.token) as client:
                response = await client.users.get_accounts()
                accounts = []
                
                for account in response.accounts:
                    account_info = {
                        'id': account.id,
                        'type': AccountType(account.type).name,
                        'status': AccountStatus(account.status).name,
                        'name': account.name,
                        'portfolio_value': 0.0
                    }
                    
                    try:
                        portfolio = await client.operations.get_portfolio(account_id=account.id)
                        total_value = 0
                        for position in portfolio.positions:
                            if hasattr(position, 'current_price'):
                                price = quotation_to_decimal(position.current_price)
                                quantity = quotation_to_decimal(position.quantity)
                                total_value += float(price * quantity)
                        account_info['portfolio_value'] = total_value
                    except Exception as e:
                        logger.warning(f"Could not get portfolio for account {account.id}: {e}")
                    
                    accounts.append(account_info)
                
                logger.info(f"Successfully retrieved {len(accounts)} accounts")
                return sorted(accounts, key=lambda x: x['portfolio_value'], reverse=True)
                
        except Exception as e:
            logger.error(f"Error getting accounts: {e}")
            return []

    async def validate_account(self, account_id: str) -> bool:
        """Проверка, что счет существует и доступен"""
        try:
            logger.info(f"Validating account {account_id}")
            async with AsyncClient(self.token) as client:
                accounts = await client.users.get_accounts()
                account_ids = [account.id for account in accounts.accounts]
                is_valid = account_id in account_ids
                logger.info(f"Account {account_id} validation result: {is_valid}")
                return is_valid
        except Exception as e:
            logger.error(f"Error validating account {account_id}: {e}")
            return False

    def get_account_emoji(self, account_name: str) -> str:
        """Получить emoji для типа счета"""
        name_lower = account_name.lower()
        if "брокерский" in name_lower:
            return "📈"
        elif "инвест" in name_lower:
            return "💰"
        elif "иис" in name_lower:
            return "🏦"
        else:
            return "💼"
        