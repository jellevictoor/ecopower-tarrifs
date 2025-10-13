"""Service for calculating monthly electricity costs with fixed tariff"""
from datetime import datetime

from ..domain.models import MonthlyCostBreakdown
from ..domain.fixed_tariff_calculator import FixedTariffCalculator
from ..ports.repositories import PowerReadingRepository


class FixedMonthlyCostCalculationService:
    """
    Service for orchestrating monthly cost calculations with fixed tariff.
    Only needs power readings (no EPEX prices needed).
    Depends on repository interface (port), not concrete implementation.
    """

    def __init__(
        self,
        power_repository: PowerReadingRepository
    ):
        """
        Initialize the service with repository dependencies

        Args:
            power_repository: Repository for power consumption/injection data
        """
        self.power_repository = power_repository
        self.calculator = FixedTariffCalculator

    def calculate_monthly_cost(self, year: int, month: int) -> MonthlyCostBreakdown:
        """
        Calculate the total cost for a specific month using fixed tariff

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

        # Fetch data from repositories (only power readings needed)
        consumption_readings = self.power_repository.get_consumption_readings(
            start_date, end_date
        )
        injection_readings = self.power_repository.get_injection_readings(
            start_date, end_date
        )

        # Calculate monthly cost using fixed tariff domain logic
        return self.calculator.calculate_monthly_cost(
            year=year,
            month=month,
            consumption_readings=consumption_readings,
            injection_readings=injection_readings
        )

    def calculate_current_month_cost(self) -> MonthlyCostBreakdown:
        """
        Calculate the cost for the current month using fixed tariff

        Returns:
            Complete monthly cost breakdown for current month
        """
        now = datetime.now()
        return self.calculate_monthly_cost(now.year, now.month)
