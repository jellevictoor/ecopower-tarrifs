"""Service for calculating monthly electricity costs"""
from datetime import datetime
from typing import Dict

from ..domain.models import MonthlyCostBreakdown
from ..domain.tariff_calculator import EcopowerTariffCalculator
from ..ports.repositories import PowerReadingRepository, EpexPriceRepository


class MonthlyCostCalculationService:
    """
    Service for orchestrating monthly cost calculations.
    Depends on repository interfaces (ports), not concrete implementations.
    """

    def __init__(
        self,
        power_repository: PowerReadingRepository,
        price_repository: EpexPriceRepository
    ):
        """
        Initialize the service with repository dependencies

        Args:
            power_repository: Repository for power consumption/injection data
            price_repository: Repository for EPEX prices
        """
        self.power_repository = power_repository
        self.price_repository = price_repository
        self.calculator = EcopowerTariffCalculator

    def calculate_monthly_cost(self, year: int, month: int) -> MonthlyCostBreakdown:
        """
        Calculate the total cost for a specific month

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            Complete monthly cost breakdown
        """
        # Calculate date range for the month
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        # Fetch data from repositories
        consumption_readings = self.power_repository.get_consumption_readings(
            start_date, end_date
        )
        injection_readings = self.power_repository.get_injection_readings(
            start_date, end_date
        )
        epex_price_list = self.price_repository.get_prices(start_date, end_date)

        # Convert EPEX prices to dictionary for efficient lookup
        epex_prices: Dict[datetime, float] = {
            price.timestamp: price.price_eur_mwh
            for price in epex_price_list
        }

        # Calculate monthly cost using domain logic
        return self.calculator.calculate_monthly_cost(
            year=year,
            month=month,
            consumption_readings=consumption_readings,
            injection_readings=injection_readings,
            epex_prices=epex_prices
        )

    def calculate_current_month_cost(self) -> MonthlyCostBreakdown:
        """
        Calculate the cost for the current month

        Returns:
            Complete monthly cost breakdown for current month
        """
        now = datetime.now()
        return self.calculate_monthly_cost(now.year, now.month)
