"""Tariff calculation logic - pure business rules"""
from typing import List, Dict
from datetime import datetime

from .models import PowerReading, EpexPrice, MonthlyEnergyData, MonthlyCostBreakdown


class EcopowerTariffCalculator:
    """
    Calculates electricity costs based on Ecopower tariff structure.
    Contains only pure business logic with no external dependencies.
    """

    # Fixed monthly subscription costs (EUR/month)
    ECOPOWER_SUBSCRIPTION = 5.0
    FLUVIUS_SUBSCRIPTION = 2.0

    # Energy cost coefficients (based on EPEX price in EUR/MWh)
    CONSUMPTION_COEFFICIENT = 0.00102
    CONSUMPTION_FIXED = 0.004

    # Injection revenue coefficients (based on EPEX price in EUR/MWh)
    INJECTION_COEFFICIENT = 0.00098
    INJECTION_FIXED = -0.015

    # Distribution and other costs (EUR/kWh)
    DISTRIBUTION_TARIFF = 0.0704386
    INJECTION_TARIFF = 0.0017510
    GSC_TARIFF = 0.011
    WKK_TARIFF = 0.00392

    # Capacity tariff (EUR/kW/year)
    CAPACITY_TARIFF_YEARLY = 56.93

    @classmethod
    def calculate_fixed_cost(cls) -> float:
        """Calculate monthly fixed subscription cost"""
        return cls.ECOPOWER_SUBSCRIPTION + cls.FLUVIUS_SUBSCRIPTION

    @classmethod
    def calculate_energy_cost_per_kwh(cls, epex_price_eur_mwh: float) -> float:
        """
        Calculate energy cost per kWh based on EPEX day-ahead price

        Args:
            epex_price_eur_mwh: EPEX price in EUR/MWh

        Returns:
            Cost in EUR/kWh
        """
        return cls.CONSUMPTION_COEFFICIENT * epex_price_eur_mwh + cls.CONSUMPTION_FIXED

    @classmethod
    def calculate_energy_revenue_per_kwh(cls, epex_price_eur_mwh: float) -> float:
        """
        Calculate energy injection revenue per kWh based on EPEX day-ahead price

        Args:
            epex_price_eur_mwh: EPEX price in EUR/MWh

        Returns:
            Revenue in EUR/kWh
        """
        return cls.INJECTION_COEFFICIENT * epex_price_eur_mwh + cls.INJECTION_FIXED

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
    def calculate_quarterly_energy_costs(
        cls,
        consumption_readings: List[PowerReading],
        injection_readings: List[PowerReading],
        epex_prices: Dict[datetime, float]
    ) -> tuple[float, float, MonthlyEnergyData]:
        """
        Calculate energy costs and revenues for a period based on 15-minute readings

        Args:
            consumption_readings: List of power consumption readings
            injection_readings: List of power injection readings
            epex_prices: Dictionary mapping timestamps to EPEX prices (EUR/MWh)

        Returns:
            Tuple of (total_energy_cost, total_energy_revenue, aggregated_data)
        """
        total_energy_cost = 0.0
        total_energy_revenue = 0.0
        total_kwh_delivered = 0.0
        total_kwh_returned = 0.0
        max_power_kw = 0.0

        # Process consumption readings
        for reading in consumption_readings:
            # Convert 15-minute power reading to kWh
            kwh_15min = reading.power_kw * 0.25
            total_kwh_delivered += kwh_15min

            # Track peak power
            if reading.power_kw > max_power_kw:
                max_power_kw = reading.power_kw

            # Get EPEX price for this timestamp
            epex_price = epex_prices.get(reading.timestamp, 0.0)

            # Calculate cost for this period
            cost_per_kwh = cls.calculate_energy_cost_per_kwh(epex_price)
            total_energy_cost += cost_per_kwh * kwh_15min

        # Process injection readings
        for reading in injection_readings:
            # Convert 15-minute power reading to kWh
            kwh_15min = reading.power_kw * 0.25
            total_kwh_returned += kwh_15min

            # Get EPEX price for this timestamp
            epex_price = epex_prices.get(reading.timestamp, 0.0)

            # Calculate revenue for this period
            revenue_per_kwh = cls.calculate_energy_revenue_per_kwh(epex_price)
            total_energy_revenue += revenue_per_kwh * kwh_15min

        energy_data = MonthlyEnergyData(
            total_kwh_delivered=total_kwh_delivered,
            total_kwh_returned=total_kwh_returned,
            peak_power_kw=max_power_kw
        )

        return total_energy_cost, total_energy_revenue, energy_data

    @classmethod
    def calculate_monthly_cost(
        cls,
        year: int,
        month: int,
        consumption_readings: List[PowerReading],
        injection_readings: List[PowerReading],
        epex_prices: Dict[datetime, float]
    ) -> MonthlyCostBreakdown:
        """
        Calculate complete monthly cost breakdown

        Args:
            year: Year of the month
            month: Month number (1-12)
            consumption_readings: List of power consumption readings
            injection_readings: List of power injection readings
            epex_prices: Dictionary mapping timestamps to EPEX prices

        Returns:
            Complete monthly cost breakdown
        """
        # Calculate energy costs and aggregate data
        energy_cost, energy_revenue, energy_data = cls.calculate_quarterly_energy_costs(
            consumption_readings,
            injection_readings,
            epex_prices
        )

        # Calculate all cost components
        fixed_cost = cls.calculate_fixed_cost()
        distribution_cost = cls.calculate_distribution_cost(energy_data.total_kwh_delivered)
        injection_cost = cls.calculate_injection_cost(energy_data.total_kwh_returned)
        gsc_cost = cls.calculate_gsc_cost(energy_data.total_kwh_delivered)
        wkk_cost = cls.calculate_wkk_cost(energy_data.total_kwh_delivered)
        capacity_cost = cls.calculate_monthly_capacity_cost(energy_data.peak_power_kw)

        return MonthlyCostBreakdown(
            year=year,
            month=month,
            fixed_cost=fixed_cost,
            energy_cost=energy_cost,
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
