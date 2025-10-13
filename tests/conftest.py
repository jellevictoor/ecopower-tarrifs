"""Pytest configuration and fixtures"""
import pytest
from datetime import datetime
from typing import List

from ecopower_tarrifs.domain.models import PowerReading, EpexPrice
from ecopower_tarrifs.ports.repositories import PowerReadingRepository, EpexPriceRepository


class MockPowerReadingRepository(PowerReadingRepository):
    """Mock implementation for testing"""

    def __init__(self, consumption_data: List[PowerReading], injection_data: List[PowerReading]):
        self.consumption_data = consumption_data
        self.injection_data = injection_data

    def get_consumption_readings(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[PowerReading]:
        return [
            r for r in self.consumption_data
            if start_date <= r.timestamp < end_date
        ]

    def get_injection_readings(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[PowerReading]:
        return [
            r for r in self.injection_data
            if start_date <= r.timestamp < end_date
        ]


class MockEpexPriceRepository(EpexPriceRepository):
    """Mock implementation for testing"""

    def __init__(self, price_data: List[EpexPrice]):
        self.price_data = price_data

    def get_prices(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[EpexPrice]:
        return [
            p for p in self.price_data
            if start_date <= p.timestamp < end_date
        ]


@pytest.fixture
def sample_consumption_readings():
    """Sample consumption readings for testing"""
    base_time = datetime(2025, 10, 1, 0, 0, 0)
    return [
        PowerReading(
            timestamp=base_time.replace(hour=i // 4, minute=(i % 4) * 15),
            power_kw=2.5 + (i % 10) * 0.1  # Varying power between 2.5-3.4 kW
        )
        for i in range(96)  # One day of 15-minute readings
    ]


@pytest.fixture
def sample_injection_readings():
    """Sample injection readings for testing"""
    base_time = datetime(2025, 10, 1, 0, 0, 0)
    return [
        PowerReading(
            timestamp=base_time.replace(hour=i // 4, minute=(i % 4) * 15),
            power_kw=1.0 + (i % 8) * 0.1  # Varying power between 1.0-1.7 kW
        )
        for i in range(96)  # One day of 15-minute readings
    ]


@pytest.fixture
def sample_epex_prices():
    """Sample EPEX prices for testing"""
    base_time = datetime(2025, 10, 1, 0, 0, 0)
    return [
        EpexPrice(
            timestamp=base_time.replace(hour=i // 4, minute=(i % 4) * 15),
            price_eur_mwh=50.0 + (i % 20) * 2.0  # Varying prices between 50-88 EUR/MWh
        )
        for i in range(96)  # One day of 15-minute readings
    ]


@pytest.fixture
def mock_power_repository(sample_consumption_readings, sample_injection_readings):
    """Mock power repository with sample data"""
    return MockPowerReadingRepository(
        consumption_data=sample_consumption_readings,
        injection_data=sample_injection_readings
    )


@pytest.fixture
def mock_price_repository(sample_epex_prices):
    """Mock price repository with sample data"""
    return MockEpexPriceRepository(price_data=sample_epex_prices)
