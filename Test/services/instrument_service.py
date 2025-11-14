import logging
from tinkoff.invest import AsyncClient, InstrumentIdType

logger = logging.getLogger(__name__)

class InstrumentService:
    def __init__(self, token: str):
        self.token = token

    async def get_instrument_name(self, figi: str) -> str:
        """Получение названия инструмента по FIGI"""
        try:
            async with AsyncClient(self.token) as client:
                instrument = await client.instruments.get_instrument_by(
                    id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI, 
                    id=figi
                )
                return instrument.instrument.name
        except Exception as e:
            logger.error(f"Error getting instrument name for FIGI {figi}: {e}")
            return "Неизвестный инструмент"
        