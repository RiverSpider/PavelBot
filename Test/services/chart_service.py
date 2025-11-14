import logging
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
import io
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Tuple
from tinkoff.invest import AsyncClient, OperationType, OperationState
import asyncio

logger = logging.getLogger(__name__)

class ChartService:
    def __init__(self, token: str):
        self.token = token

    async def generate_capital_chart(self, account_ids: List[str], period: str) -> io.BytesIO:
        """Генерация графика изменения капитала за период для нескольких счетов"""
        try:
            operations = await self._get_operations_for_accounts_period(account_ids, period)
            if not operations:
                return None

            daily_data = await self._calculate_daily_capital(operations, period)
            
            return await self._create_capital_chart(daily_data, period)
            
        except Exception as e:
            logger.error(f"Error generating capital chart: {e}")
            return None

    async def generate_income_chart(self, account_ids: List[str], period: str) -> io.BytesIO:
        """Генерация графика доходности по дням для нескольких счетов"""
        try:
            operations = await self._get_operations_for_accounts_period(account_ids, period)
            if not operations:
                return None

            daily_income = await self._calculate_daily_income(operations, period)
            
            return await self._create_income_chart(daily_income, period)
            
        except Exception as e:
            logger.error(f"Error generating income chart: {e}")
            return None

    async def _get_operations_for_accounts_period(self, account_ids: List[str], period: str) -> List:
        """Получение операций за указанный период для нескольких счетов"""
        try:
            all_operations = []
            tasks = []
            
            for account_id in account_ids:
                task = self._get_operations_for_period(account_id, period)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Error getting operations: {result}")
                    continue
                all_operations.extend(result)
            
            return all_operations
                
        except Exception as e:
            logger.error(f"Error getting operations for period: {e}")
            return []

    async def _get_operations_for_period(self, account_id: str, period: str) -> List:
        """Получение операций за указанный период для одного счета"""
        try:
            async with AsyncClient(self.token) as client:
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

                operations = await client.operations.get_operations(
                    account_id=account_id,
                    from_=start_date,
                    to=end_date,
                    state=OperationState.OPERATION_STATE_EXECUTED
                )
                return operations.operations
                
        except Exception as e:
            logger.error(f"Error getting operations for period: {e}")
            return []

    async def _calculate_daily_capital(self, operations: List, period: str) -> List[Dict]:
        """Расчет изменения капитала по дням для всех операций"""
        try:
            operations.sort(key=lambda x: x.date)
            
            daily_data = []
            current_capital = Decimal('0')
            
            operations_by_date = {}
            for op in operations:
                date_key = op.date.date()
                if date_key not in operations_by_date:
                    operations_by_date[date_key] = []
                operations_by_date[date_key].append(op)
            
            dates = sorted(operations_by_date.keys())
            
            for date in dates:
                day_operations = operations_by_date[date]
                day_income = Decimal('0')
                
                for op in day_operations:
                    amount = self._operation_to_decimal(op)
                    if (op.operation_type in [OperationType.OPERATION_TYPE_COUPON, 
                                            OperationType.OPERATION_TYPE_DIVIDEND] and amount > 0):
                        day_income += amount
                    elif amount < 0 and "COMMISSION" in str(op.operation_type):
                        day_income += amount
                
                current_capital += day_income
                
                daily_data.append({
                    'date': date,
                    'capital': float(current_capital),
                    'daily_income': float(day_income)
                })
            
            return daily_data
            
        except Exception as e:
            logger.error(f"Error calculating daily capital: {e}")
            return []

    async def _calculate_daily_income(self, operations: List, period: str) -> List[Dict]:
        """Расчет доходности по дням для всех операций"""
        try:
            operations.sort(key=lambda x: x.date)
            
            daily_income = {}
            
            for op in operations:
                date_key = op.date.date()
                amount = self._operation_to_decimal(op)
                
                if date_key not in daily_income:
                    daily_income[date_key] = Decimal('0')
                
                if (op.operation_type in [OperationType.OPERATION_TYPE_COUPON, 
                                        OperationType.OPERATION_TYPE_DIVIDEND] and amount > 0):
                    daily_income[date_key] += amount
                elif amount < 0 and "COMMISSION" in str(op.operation_type):
                    daily_income[date_key] += amount
            
            result = [{'date': date, 'income': float(income)} 
                     for date, income in sorted(daily_income.items())]
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating daily income: {e}")
            return []

    async def _create_capital_chart(self, daily_data: List[Dict], period: str) -> io.BytesIO:
        """Создание графика изменения капитала"""
        try:
            if not daily_data:
                return None

            plt.style.use('dark_background')
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
            
            dates = [data['date'] for data in daily_data]
            capital = [data['capital'] for data in daily_data]
            daily_income = [data['daily_income'] for data in daily_data]
            
            ax1.plot(dates, capital, 'o-', color='#00FFAA', linewidth=2, markersize=6, label='Капитал')
            ax1.fill_between(dates, capital, alpha=0.3, color='#00FFAA')
            ax1.set_title(f'📈 Изменение капитала за {self._get_period_name(period)}', 
                         fontsize=14, fontweight='bold', pad=20)
            ax1.set_ylabel('Капитал, ₽', fontsize=12)
            ax1.grid(True, alpha=0.3)
            ax1.legend()
            
            ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}₽'))
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            
            colors = ['#00FFAA' if x >= 0 else '#FF4444' for x in daily_income]
            bars = ax2.bar(dates, daily_income, color=colors, alpha=0.7, label='Доход/расход')
            ax2.set_title('💸 Ежедневный доход/расход', fontsize=12, fontweight='bold', pad=20)
            ax2.set_ylabel('Сумма, ₽', fontsize=12)
            ax2.set_xlabel('Дата', fontsize=12)
            ax2.grid(True, alpha=0.3)
            
            for bar in bars:
                height = bar.get_height()
                if height != 0:
                    ax2.text(bar.get_x() + bar.get_width()/2., height,
                            f'{height:+.0f}₽',
                            ha='center', va='bottom' if height > 0 else 'top', 
                            fontsize=9, fontweight='bold')
            
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close()
            
            return buf
            
        except Exception as e:
            logger.error(f"Error creating capital chart: {e}")
            plt.close()
            return None

    async def _create_income_chart(self, daily_income: List[Dict], period: str) -> io.BytesIO:
        """Создание графика доходности"""
        try:
            if not daily_income:
                return None

            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(12, 6))
            
            dates = [data['date'] for data in daily_income]
            income = [data['income'] for data in daily_income]
            
            cumulative_income = np.cumsum(income)
            
            ax.plot(dates, cumulative_income, 'o-', color='#00AAFF', linewidth=3, 
                   label='Накопительный доход', markersize=6)
            ax.fill_between(dates, cumulative_income, alpha=0.3, color='#00AAFF')
            
            ax2 = ax.twinx()
            colors = ['#00FFAA' if x >= 0 else '#FF4444' for x in income]
            bars = ax2.bar(dates, income, alpha=0.5, color=colors, label='Ежедневный доход')
            
            ax.set_title(f'💰 Доходность за {self._get_period_name(period)}', 
                        fontsize=14, fontweight='bold', pad=20)
            ax.set_ylabel('Накопительный доход, ₽', fontsize=12)
            ax2.set_ylabel('Ежедневный доход, ₽', fontsize=12)
            ax.set_xlabel('Дата', fontsize=12)
            
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}₽'))
            ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:,.0f}₽'))
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper left')
            ax2.legend(loc='upper right')
            
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close()
            
            return buf
            
        except Exception as e:
            logger.error(f"Error creating income chart: {e}")
            plt.close()
            return None

    def _get_period_name(self, period: str) -> str:
        """Получение названия периода на русском"""
        period_names = {
            'day': 'день',
            'week': 'неделю', 
            'month': 'месяц',
            'year': 'год',
            'all_time': 'все время'
        }
        return period_names.get(period, 'период')

    def _operation_to_decimal(self, operation) -> Decimal:
        """Конвертация операции в decimal"""
        try:
            if hasattr(operation, 'payment') and operation.payment:
                from tinkoff.invest.utils import quotation_to_decimal
                return quotation_to_decimal(operation.payment)
            return Decimal('0')
        except Exception as e:
            logger.error(f"Error converting operation to decimal: {e}")
            return Decimal('0')
        