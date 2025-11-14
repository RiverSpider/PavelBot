import logging
from datetime import datetime, timedelta
from typing import List, Dict
from decimal import Decimal
from tinkoff.invest import AsyncClient, Operation, OperationState, OperationType
from tinkoff.invest.utils import quotation_to_decimal
import asyncio

logger = logging.getLogger(__name__)

class OperationService:
    def __init__(self, token: str):
        self.token = token

    async def get_operations(self, account_id: str, from_date: datetime, to_date: datetime) -> List[Operation]:
        """Получение операций за указанный период для одного счета"""
        try:
            async with AsyncClient(self.token) as client:
                operations = await client.operations.get_operations(
                    account_id=account_id,
                    from_=from_date,
                    to=to_date,
                    state=OperationState.OPERATION_STATE_EXECUTED
                )
                return operations.operations
        except Exception as e:
            logger.error(f"Error getting operations for account {account_id}: {e}")
            return []

    async def get_operations_for_accounts(self, account_ids: List[str], from_date: datetime, to_date: datetime) -> List[Operation]:
        """Получение операций за указанный период для нескольких счетов"""
        try:
            all_operations = []
            tasks = []
            
            for account_id in account_ids:
                task = self.get_operations(account_id, from_date, to_date)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error getting operations: {result}")
                    continue
                all_operations.extend(result)
            
            return all_operations
        except Exception as e:
            logger.error(f"Error getting operations for multiple accounts: {e}")
            return []

    def _operation_to_decimal(self, operation: Operation) -> Decimal:
        """Конвертация операции в decimal"""
        try:
            if hasattr(operation, 'payment') and operation.payment:
                return quotation_to_decimal(operation.payment)
            return Decimal('0')
        except Exception as e:
            logger.error(f"Error converting operation to decimal: {e}")
            return Decimal('0')

    async def calculate_income_for_accounts(self, account_ids: List[str], period: str) -> Dict[str, Decimal]:
        """Расчет дохода за указанный период для нескольких счетов"""
        try:
            end_date = datetime.now()
            
            if period == 'day':
                start_date = end_date - timedelta(days=1)
            elif period == 'week':
                start_date = end_date - timedelta(weeks=1)
            elif period == 'month':
                start_date = end_date - timedelta(days=30)
            elif period == 'year':
                start_date = end_date - timedelta(days=365)
            elif period == 'all_time':
                start_date = end_date - timedelta(days=365*10)
            else:
                start_date = end_date - timedelta(days=7)

            operations = await self.get_operations_for_accounts(account_ids, start_date, end_date)
            
            return await self._process_income_calculation(operations, period)
        except Exception as e:
            logger.error(f"Error calculating income for multiple accounts period {period}: {e}")
            return self._get_empty_income_result(period)

    async def _process_income_calculation(self, operations: List[Operation], period: str) -> Dict[str, Decimal]:
        """Обработка расчета дохода для списка операций"""
        total_income = Decimal('0')
        bond_income = Decimal('0')
        dividend_income = Decimal('0')
        commission_expenses = Decimal('0')

        for operation in operations:
            try:
                amount = self._operation_to_decimal(operation)
                
                if amount > 0:
                    if operation.operation_type == OperationType.OPERATION_TYPE_COUPON:
                        bond_income += amount
                        total_income += amount
                    elif operation.operation_type == OperationType.OPERATION_TYPE_DIVIDEND:
                        dividend_income += amount
                        total_income += amount
                elif amount < 0:
                    if str(operation.operation_type) == "OperationType.OPERATION_TYPE_BROKER_COMMISSION":
                        commission_expenses += abs(amount)
            except Exception as e:
                logger.warning(f"Error processing operation {operation.operation_type}: {e}")
                continue

        return {
            'total_income': total_income,
            'bond_income': bond_income,
            'dividend_income': dividend_income,
            'commission_expenses': commission_expenses,
            'period': period
        }

    async def calculate_total_capital_growth_for_accounts(self, account_ids: List[str]) -> Dict[str, Decimal]:
        """Расчет общего роста капитала за все время для нескольких счетов"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365*10)
            
            operations = await self.get_operations_for_accounts(account_ids, start_date, end_date)
            
            return await self._process_capital_growth_calculation(operations)
        except Exception as e:
            logger.error(f"Error calculating total capital growth for multiple accounts: {e}")
            return self._get_empty_growth_result()

    async def _process_capital_growth_calculation(self, operations: List[Operation]) -> Dict[str, Decimal]:
        """Обработка расчета роста капитала для списка операций"""
        total_growth = Decimal('0')
        total_invested = Decimal('0')
        total_withdrawn = Decimal('0')
        
        for operation in operations:
            try:
                amount = self._operation_to_decimal(operation)
                
                if amount > 0:
                    if operation.operation_type in [
                        OperationType.OPERATION_TYPE_COUPON,
                        OperationType.OPERATION_TYPE_DIVIDEND,
                        OperationType.OPERATION_TYPE_INPUT
                    ]:
                        total_growth += amount
                    elif operation.operation_type == OperationType.OPERATION_TYPE_INPUT:
                        total_invested += amount
                elif amount < 0:
                    if operation.operation_type == OperationType.OPERATION_TYPE_OUTPUT:
                        total_withdrawn += abs(amount)
                    elif "COMMISSION" in str(operation.operation_type):
                        total_growth += amount
                        
            except Exception as e:
                logger.warning(f"Error processing operation for capital growth: {e}")
                continue

        return {
            'total_growth': total_growth,
            'total_invested': total_invested,
            'total_withdrawn': total_withdrawn,
            'net_growth': total_growth - total_withdrawn
        }

    def _get_empty_income_result(self, period: str) -> Dict[str, Decimal]:
        return {
            'total_income': Decimal('0'),
            'bond_income': Decimal('0'),
            'dividend_income': Decimal('0'),
            'commission_expenses': Decimal('0'),
            'period': period
        }

    def _get_empty_growth_result(self) -> Dict[str, Decimal]:
        return {
            'total_growth': Decimal('0'),
            'total_invested': Decimal('0'),
            'total_withdrawn': Decimal('0'),
            'net_growth': Decimal('0')
        }
    