"""Repository interfaces (ports) for data access"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from ..domain.models import PowerReading, EpexPrice


class PowerReadingRepository(ABC):
    """Interface for fetching power consumption and injection data"""

    @abstractmethod
    def get_consumption_readings(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[PowerReading]:
        """
        Fetch power consumption readings for a date range

        Args:
            start_date: Start of the period
            end_date: End of the period

        Returns:
            List of power consumption readings
        """
        pass

    @abstractmethod
    def get_injection_readings(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[PowerReading]:
        """
        Fetch power injection readings for a date range

        Args:
            start_date: Start of the period
            end_date: End of the period

        Returns:
            List of power injection readings
        """
        pass


class EpexPriceRepository(ABC):
    """Interface for fetching EPEX day-ahead prices"""

    @abstractmethod
    def get_prices(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[EpexPrice]:
        """
        Fetch EPEX day-ahead prices for a date range

        Args:
            start_date: Start of the period
            end_date: End of the period

        Returns:
            List of EPEX prices
        """
        pass
