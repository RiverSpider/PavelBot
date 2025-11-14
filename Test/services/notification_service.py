import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from decimal import Decimal
from tinkoff.invest import AsyncClient, InstrumentIdType, GetDividendsRequest, GetBondCouponsRequest
from tinkoff.invest.utils import quotation_to_decimal
import aiofiles
import json
import os

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, token: str):
        self.token = token

    async def get_upcoming_payments(self, figi_list: List[str]) -> Dict[str, List[Dict]]:
        """Получение предстоящих выплат по инструментам в портфеле"""
        try:
            async with AsyncClient(self.token) as client:
                upcoming_payments = {
                    'dividends': [],
                    'coupons': [],
                    'other': []
                }

                for figi in figi_list:
                    try:
                        # Получаем информацию об инструменте
                        instrument = await client.instruments.get_instrument_by(
                            id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
                            id=figi
                        )
                        
                        instrument_type = str(instrument.instrument.instrument_type).lower()
                        
                        # Для акций получаем дивиденды
                        if 'share' in instrument_type:
                            dividends = await self._get_dividends_for_instrument(client, instrument.instrument.uid)
                            upcoming_payments['dividends'].extend(dividends)
                        
                        # Для облигаций получаем купоны
                        elif 'bond' in instrument_type:
                            coupons = await self._get_coupons_for_instrument(client, figi)
                            upcoming_payments['coupons'].extend(coupons)
                            
                    except Exception as e:
                        logger.warning(f"Error getting payments for FIGI {figi}: {e}")
                        continue

                return upcoming_payments
                
        except Exception as e:
            logger.error(f"Error getting upcoming payments: {e}")
            return {'dividends': [], 'coupons': [], 'other': []}

    async def _get_dividends_for_instrument(self, client, instrument_uid: str) -> List[Dict]:
        """Получение дивидендов для инструмента"""
        try:
            dividends_response = await client.instruments.get_dividends(
                id=instrument_uid
            )
            
            upcoming_dividends = []
            for dividend in dividends_response.dividends:
                if dividend.payment_date.date() > datetime.now().date():
                    upcoming_dividends.append({
                        'type': 'dividend',
                        'instrument_uid': instrument_uid,
                        'payment_date': dividend.payment_date,
                        'dividend_net': float(quotation_to_decimal(dividend.dividend_net)),
                        'currency': dividend.dividend_net.currency
                    })
            
            return upcoming_dividends
        except Exception as e:
            logger.warning(f"Error getting dividends for instrument {instrument_uid}: {e}")
            return []

    async def _get_coupons_for_instrument(self, client, figi: str) -> List[Dict]:
        """Получение купонов для облигации"""
        try:
            from_date = datetime.now() - timedelta(days=30)
            to_date = datetime.now() + timedelta(days=60)
            
            coupons_response = await client.instruments.get_bond_coupons(
                figi=figi,
                from_=from_date,
                to=to_date
            )
            
            upcoming_coupons = []
            for coupon in coupons_response.events:
                if coupon.coupon_date.date() > datetime.now().date():
                    upcoming_coupons.append({
                        'type': 'coupon',
                        'figi': figi,
                        'coupon_date': coupon.coupon_date,
                        'coupon_number': coupon.coupon_number,
                        'pay_one_bond': float(quotation_to_decimal(coupon.pay_one_bond)),
                        'currency': coupon.pay_one_bond.currency
                    })
            
            return upcoming_coupons
        except Exception as e:
            logger.warning(f"Error getting coupons for FIGI {figi}: {e}")
            return []

    async def get_daily_summary(self, account_ids: List[str], from_date: datetime, to_date: datetime) -> Dict:
        """Получение сводки за день по операциям"""
        try:
            async with AsyncClient(self.token) as client:
                total_income = Decimal('0')
                total_expense = Decimal('0')
                operations_summary = []

                for account_id in account_ids:
                    try:
                        operations = await client.operations.get_operations(
                            account_id=account_id,
                            from_=from_date,
                            to=to_date,
                            state=1  # OPERATION_STATE_EXECUTED
                        )
                        
                        for operation in operations.operations:
                            amount = quotation_to_decimal(operation.payment) if operation.payment else Decimal('0')
                            
                            if amount > 0:
                                total_income += amount
                            elif amount < 0:
                                total_expense += abs(amount)
                            
                            operation_info = {
                                'date': operation.date,
                                'type': str(operation.operation_type),
                                'amount': float(amount),
                                'currency': operation.payment.currency if operation.payment else 'rub',
                                'description': operation.description or '',
                                'status': str(operation.state)
                            }
                            operations_summary.append(operation_info)
                            
                    except Exception as e:
                        logger.warning(f"Error getting operations for account {account_id}: {e}")
                        continue

                return {
                    'total_income': float(total_income),
                    'total_expense': float(total_expense),
                    'net_flow': float(total_income - total_expense),
                    'operations_count': len(operations_summary),
                    'operations': operations_summary
                }
                
        except Exception as e:
            logger.error(f"Error getting daily summary: {e}")
            return {
                'total_income': 0.0,
                'total_expense': 0.0,
                'net_flow': 0.0,
                'operations_count': 0,
                'operations': []
            }

    async def format_upcoming_payments_message(self, upcoming_payments: Dict) -> str:
        """Форматирование сообщения о предстоящих выплатах"""
        message = "📅 *Предстоящие выплаты на этой неделе:*\n\n"
        
        # Дивиденды
        if upcoming_payments['dividends']:
            message += "💵 *Дивиденды:*\n"
            for dividend in upcoming_payments['dividends'][:50]:  # Ограничим 5 дивидендами
                date_str = dividend['payment_date'].strftime("%d.%m.%Y")
                message += f"• {date_str}: {dividend['dividend_net']:.2f} {dividend['currency']}\n"
            message += "\n"
        
        # Купоны
        if upcoming_payments['coupons']:
            message += "🎯 *Купоны по облигациям:*\n"
            for coupon in upcoming_payments['coupons'][:50]:  # Ограничим 5 купонами
                date_str = coupon['coupon_date'].strftime("%d.%m.%Y")
                message += f"• {date_str}: {coupon['pay_one_bond']:.2f} {coupon['currency']}\n"
            message += "\n"
        
        if not upcoming_payments['dividends'] and not upcoming_payments['coupons']:
            message += "ℹ️ На этой неделе выплат не запланировано\n"
        
        message += "\n💡 *Совет:* Регулярно проверяйте календарь выплат!"
        
        return message

    async def format_daily_summary_message(self, daily_summary: Dict) -> str:
        """Форматирование ежедневной сводки"""
        message = "📊 *Финансовая сводка за день:*\n\n"
        
        message += f"💰 *Пришло средств:* {daily_summary['total_income']:,.2f} ₽\n"
        message += f"💸 *Ушло средств:* {daily_summary['total_expense']:,.2f} ₽\n"
        message += f"💎 *Итоговый поток:* {daily_summary['net_flow']:,.2f} ₽\n"
        message += f"📋 *Количество операций:* {daily_summary['operations_count']}\n"
        
        if daily_summary['net_flow'] > 0:
            message += "\n✅ *Отличный день!* Превышение доходов над расходами.\n"
        elif daily_summary['net_flow'] < 0:
            message += "\n⚠️ *Внимание!* Расходы превысили доходы.\n"
        else:
            message += "\n➖ *Сбалансированный день.* Доходы равны расходам.\n"
        
        return message
    