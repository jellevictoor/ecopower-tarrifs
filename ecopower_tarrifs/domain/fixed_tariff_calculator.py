"""Fixed tariff calculation logic - Groene Burgerstroom"""
from typing import List
from datetime import datetime

from .models import PowerReading, MonthlyEnergyData, MonthlyCostBreakdown


class FixedTariffCalculator:
    """
    Calculates electricity costs based on Ecopower fixed tariff (Groene Burgerstroom).
    Contains only pure business logic with no external dependencies.
    """

    # Fixed monthly subscription costs (EUR/month)
    ECOPOWER_SUBSCRIPTION = 5.0
    FLUVIUS_SUBSCRIPTION = 2.0  # Monthly component

    # Fixed energy rates (EUR/kWh)
    ENERGY_RATE = 0.1187  # 50% fixed (0.17) + 50% variable (0.067423171)

    # Injection compensation (EUR/kWh) - negative means you receive money
    INJECTION_RATE = -0.0200

    # Distribution and other costs (EUR/kWh)
    DISTRIBUTION_TARIFF = 0.0704386
    INJECTION_TARIFF = 0.0017510
    GSC_TARIFF = 0.011
    WKK_TARIFF = 0.00392

    # Capacity tariff (EUR/kW/year) - Fluvius
    CAPACITY_TARIFF_YEARLY = 56.93

    # Fluvius yearly fixed cost
    FLUVIUS_YEARLY_FIXED = 17.51

    # Government taxes for residential customers (EUR/kWh)
    ENERGY_CONTRIBUTION = 0.0019261

    # Tiered excise tax for residential (EUR/kWh)
    EXCISE_TIER_1 = 0.04748  # 0-3,000 kWh
    EXCISE_TIER_2 = 0.04748  # 3,000-20,000 kWh
    EXCISE_TIER_3 = 0.04546  # 20,000-50,000 kWh
    EXCISE_TIER_4 = 0.04478  # 50,000-1,000,000 kWh

    # Energy fund contribution (EUR/month)
    ENERGY_FUND_MONTHLY = 0.005

    @classmethod
    def calculate_fixed_cost(cls) -> float:
        """Calculate monthly fixed subscription cost"""
        return cls.ECOPOWER_SUBSCRIPTION + cls.FLUVIUS_SUBSCRIPTION + cls.ENERGY_FUND_MONTHLY

    @classmethod
    def calculate_excise_tax(cls, total_kwh: float) -> float:
        """
        Calculate tiered excise tax based on total consumption

        Args:
            total_kwh: Total consumption in kWh

        Returns:
            Total excise tax in EUR
        """
        excise = 0.0

        if total_kwh <= 3000:
            # Tier 1: 0-3,000 kWh
            excise = total_kwh * cls.EXCISE_TIER_1
        elif total_kwh <= 20000:
            # Tier 1 + Tier 2
            excise = 3000 * cls.EXCISE_TIER_1 + (total_kwh - 3000) * cls.EXCISE_TIER_2
        elif total_kwh <= 50000:
            # Tier 1 + Tier 2 + Tier 3
            excise = (
                3000 * cls.EXCISE_TIER_1 +
                17000 * cls.EXCISE_TIER_2 +
                (total_kwh - 20000) * cls.EXCISE_TIER_3
            )
        else:
            # All tiers
            excise = (
                3000 * cls.EXCISE_TIER_1 +
                17000 * cls.EXCISE_TIER_2 +
                30000 * cls.EXCISE_TIER_3 +
                (total_kwh - 50000) * cls.EXCISE_TIER_4
            )

        return excise

    @classmethod
    def calculate_energy_cost(cls, kwh: float) -> float:
        """
        Calculate fixed energy cost (no EPEX dependency)

        Args:
            kwh: Energy consumption in kWh

        Returns:
            Energy cost in EUR
        """
        return kwh * cls.ENERGY_RATE

    @classmethod
    def calculate_energy_revenue(cls, kwh: float) -> float:
        """
        Calculate fixed injection revenue (you get paid)

        Args:
            kwh: Energy injected in kWh

        Returns:
            Revenue in EUR (positive = you receive money)
        """
        # Rate is negative, so multiply by -1 to get positive revenue
        return kwh * (-cls.INJECTION_RATE)

    @classmethod
    def calculate_energy_contribution(cls, kwh: float) -> float:
        """Calculate government energy contribution"""
        return kwh * cls.ENERGY_CONTRIBUTION

    @classmethod
    def calculate_distribution_cost(cls, kwh: float) -> float:
        """Calculate distribution network cost"""
        return kwh * cls.DISTRIBUTION_TARIFF

    @classmethod
    def calculate_injection_cost(cls, kwh: float) -> float:
        """Calculate injection (prosumer) tariff cost"""
        return kwh * cls.INJECTION_TARIFF

    @classmethod
    def calculate_gsc_cost(cls, kwh: float) -> float:
        """Calculate green certificate (GSC) cost"""
        return kwh * cls.GSC_TARIFF

    @classmethod
    def calculate_wkk_cost(cls, kwh: float) -> float:
        """Calculate CHP (WKK) surcharge cost"""
        return kwh * cls.WKK_TARIFF

    @classmethod
    def calculate_monthly_capacity_cost(cls, peak_power_kw: float) -> float:
        """
        Calculate monthly capacity tariff based on peak power

        Args:
            peak_power_kw: Peak power consumption in kW

        Returns:
            Monthly capacity cost in EUR
        """
        return (peak_power_kw * cls.CAPACITY_TARIFF_YEARLY) / 12

    @classmethod
    def aggregate_energy_data(
        cls,
        consumption_readings: List[PowerReading],
        injection_readings: List[PowerReading]
    ) -> MonthlyEnergyData:
        """
        Aggregate energy data from readings

        Args:
            consumption_readings: List of power consumption readings
            injection_readings: List of power injection readings

        Returns:
            Aggregated monthly energy data
        """
        total_kwh_delivered = 0.0
        total_kwh_returned = 0.0
        max_power_kw = 0.0

        # Process consumption readings
        for reading in consumption_readings:
            kwh_15min = reading.power_kw * 0.25
            total_kwh_delivered += kwh_15min

            if reading.power_kw > max_power_kw:
                max_power_kw = reading.power_kw

        # Process injection readings
        for reading in injection_readings:
            kwh_15min = reading.power_kw * 0.25
            total_kwh_returned += kwh_15min

        return MonthlyEnergyData(
            total_kwh_delivered=total_kwh_delivered,
            total_kwh_returned=total_kwh_returned,
            peak_power_kw=max_power_kw
        )

    @classmethod
    def calculate_monthly_cost(
        cls,
        year: int,
        month: int,
        consumption_readings: List[PowerReading],
        injection_readings: List[PowerReading]
    ) -> MonthlyCostBreakdown:
        """
        Calculate complete monthly cost breakdown with fixed tariff

        Args:
            year: Year of the month
            month: Month number (1-12)
            consumption_readings: List of power consumption readings
            injection_readings: List of power injection readings

        Returns:
            Complete monthly cost breakdown
        """
        # Aggregate energy data
        energy_data = cls.aggregate_energy_data(
            consumption_readings,
            injection_readings
        )

        # Calculate all cost components
        fixed_cost = cls.calculate_fixed_cost()
        energy_cost = cls.calculate_energy_cost(energy_data.total_kwh_delivered)
        energy_revenue = cls.calculate_energy_revenue(energy_data.total_kwh_returned)
        distribution_cost = cls.calculate_distribution_cost(energy_data.total_kwh_delivered)
        injection_cost = cls.calculate_injection_cost(energy_data.total_kwh_returned)
        gsc_cost = cls.calculate_gsc_cost(energy_data.total_kwh_delivered)
        wkk_cost = cls.calculate_wkk_cost(energy_data.total_kwh_delivered)
        capacity_cost = cls.calculate_monthly_capacity_cost(energy_data.peak_power_kw)

        # Government taxes
        energy_contribution = cls.calculate_energy_contribution(energy_data.total_kwh_delivered)
        excise_tax = cls.calculate_excise_tax(energy_data.total_kwh_delivered)

        # Combine all costs
        total_energy_cost = energy_cost + energy_contribution + excise_tax

        return MonthlyCostBreakdown(
            year=year,
            month=month,
            fixed_cost=fixed_cost,
            energy_cost=total_energy_cost,
            energy_revenue=energy_revenue,
            distribution_cost=distribution_cost,
            injection_cost=injection_cost,
            gsc_cost=gsc_cost,
            wkk_cost=wkk_cost,
            capacity_cost=capacity_cost,
            total_kwh_delivered=energy_data.total_kwh_delivered,
            total_kwh_returned=energy_data.total_kwh_returned,
            peak_power_kw=energy_data.peak_power_kw
        )
