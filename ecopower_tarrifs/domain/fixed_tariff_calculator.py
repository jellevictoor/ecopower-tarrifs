"""Fixed tariff calculation logic - Groene Burgerstroom"""
from typing import List
from datetime import datetime
from calendar import monthrange

from sma.ecopower import (
    GSC_EUR_KWH,
    WKK_EUR_KWH,
    BIJDRAGE_ENERGIE_EUR_KWH,
    ACCIJNS_TIER1_EUR_KWH,
    AFNAMETARIEF_EUR_PER_KWH,
)

from .models import PowerReading, MonthlyEnergyData, MonthlyCostBreakdown
from .tariff_calculator import HOUSEHOLD_REGION


class FixedTariffCalculator:
    """
    Calculates electricity costs based on Ecopower fixed tariff (Groene Burgerstroom).
    Contains only pure business logic with no external dependencies.

    Flat Fluvius/government add-ons (Afnametarief, GSC, WKK, energy contribution,
    excise tax) come from `sma` — same canonical source as EcopowerTariffCalculator,
    since these fees don't depend on which Ecopower plan (dynamic vs. fixed) you're on.
    """

    # Fixed monthly subscription (EUR/month) - Abonnementskost
    ECOPOWER_SUBSCRIPTION = 5.0

    # Fluvius data management cost (EUR/day) - Kost databeheer
    DATA_MANAGEMENT_DAILY = 0.048

    # Fixed energy rates (EUR/kWh)
    ENERGY_RATE = 0.1298  # 50% fixed (0.17) + 50% variable (0.067423171)

    # Injection compensation (EUR/kWh) - you receive money
    INJECTION_RATE = 0.0200

    # Distribution and other costs (EUR/kWh)
    DISTRIBUTION_TARIFF = AFNAMETARIEF_EUR_PER_KWH[HOUSEHOLD_REGION]  # Afnametarief
    GSC_TARIFF = GSC_EUR_KWH  # Kost GSC
    WKK_TARIFF = WKK_EUR_KWH  # Kost WKK

    # Capacity tariff (EUR/kW/year) - Capaciteitstarief
    CAPACITY_TARIFF_YEARLY = 56.93

    # Government taxes for residential customers (EUR/kWh)
    ENERGY_CONTRIBUTION = BIJDRAGE_ENERGIE_EUR_KWH  # Bijdrage op de energie
    EXCISE_TAX = ACCIJNS_TIER1_EUR_KWH  # Bijzondere accijns

    # Energy fund contribution (EUR/month) - Bijdrage Energiefonds
    ENERGY_FUND_MONTHLY = 0.00  # Reduced rate for residential

    @classmethod
    def calculate_fixed_cost(cls) -> float:
        """Calculate monthly fixed subscription cost (Ecopower only)"""
        return cls.ECOPOWER_SUBSCRIPTION

    @classmethod
    def calculate_data_management_cost(cls, days_in_month: int) -> float:
        """Calculate Fluvius data management cost (Kost databeheer)"""
        return cls.DATA_MANAGEMENT_DAILY * days_in_month

    @classmethod
    def calculate_excise_tax(cls, total_kwh: float) -> float:
        """
        Calculate excise tax (Bijzondere accijns)

        Args:
            total_kwh: Total consumption in kWh

        Returns:
            Total excise tax in EUR
        """
        return total_kwh * cls.EXCISE_TAX

    @classmethod
    def calculate_energy_fund_contribution(cls) -> float:
        """Calculate energy fund contribution (Bijdrage Energiefonds)"""
        return cls.ENERGY_FUND_MONTHLY

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
        return kwh * cls.INJECTION_RATE

    @classmethod
    def calculate_energy_contribution(cls, kwh: float) -> float:
        """Calculate government energy contribution"""
        return kwh * cls.ENERGY_CONTRIBUTION

    @classmethod
    def calculate_distribution_cost(cls, kwh: float) -> float:
        """Calculate distribution network cost"""
        return kwh * cls.DISTRIBUTION_TARIFF

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
        # Get days in month for data management cost
        days_in_month = monthrange(year, month)[1]

        # Aggregate energy data
        energy_data = cls.aggregate_energy_data(
            consumption_readings,
            injection_readings
        )

        # Calculate all cost components
        fixed_cost = cls.calculate_fixed_cost()
        data_management_cost = cls.calculate_data_management_cost(days_in_month)
        energy_cost = cls.calculate_energy_cost(energy_data.total_kwh_delivered)
        energy_revenue = cls.calculate_energy_revenue(energy_data.total_kwh_returned)
        distribution_cost = cls.calculate_distribution_cost(energy_data.total_kwh_delivered)
        gsc_cost = cls.calculate_gsc_cost(energy_data.total_kwh_delivered)
        wkk_cost = cls.calculate_wkk_cost(energy_data.total_kwh_delivered)
        capacity_cost = cls.calculate_monthly_capacity_cost(energy_data.peak_power_kw)

        # Government taxes
        energy_contribution = cls.calculate_energy_contribution(energy_data.total_kwh_delivered)
        excise_tax = cls.calculate_excise_tax(energy_data.total_kwh_delivered)
        energy_fund_contribution = cls.calculate_energy_fund_contribution()

        return MonthlyCostBreakdown(
            year=year,
            month=month,
            fixed_cost=fixed_cost,
            energy_cost=energy_cost,
            energy_revenue=energy_revenue,
            distribution_cost=distribution_cost,
            injection_cost=0.0,  # Small prosumers (≤10 kVA) pay no injection tariff
            gsc_cost=gsc_cost,
            wkk_cost=wkk_cost,
            capacity_cost=capacity_cost,
            data_management_cost=data_management_cost,
            energy_contribution=energy_contribution,
            excise_tax=excise_tax,
            energy_fund_contribution=energy_fund_contribution,
            total_kwh_delivered=energy_data.total_kwh_delivered,
            total_kwh_returned=energy_data.total_kwh_returned,
            peak_power_kw=energy_data.peak_power_kw
        )
