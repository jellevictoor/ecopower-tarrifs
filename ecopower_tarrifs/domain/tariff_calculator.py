"""Tariff calculation logic - pure business rules"""
from typing import List, Dict
from datetime import datetime
from calendar import monthrange

from sma.ecopower import (
    FluviusRegion,
    CONSUMPTION_EPEX_COEFF,
    CONSUMPTION_FIXED_EUR_KWH,
    INJECTION_EPEX_COEFF,
    INJECTION_FIXED_EUR_KWH,
    AFNAMETARIEF_EUR_PER_KWH,
    GSC_EUR_KWH,
    WKK_EUR_KWH,
    BIJDRAGE_ENERGIE_EUR_KWH,
    ACCIJNS_TIER1_EUR_KWH,
)

from .models import PowerReading, EpexPrice, MonthlyEnergyData, MonthlyCostBreakdown

# Household's Fluvius distribution region — determines which Afnametarief applies.
# Gaselwest was renamed Fluvius West on 2025-01-01.
HOUSEHOLD_REGION = FluviusRegion.WEST


class EcopowerTariffCalculator:
    """
    Calculates electricity costs based on Ecopower tariff structure.
    Contains only pure business logic with no external dependencies.

    Per-kWh economics (EPEX coefficients, Afnametarief, GSC, WKK, energy
    contribution, excise tax) come from the `sma` package — the canonical,
    dated (202601_dbs_tariefkaart.pdf), region-aware source, also used for
    curtailment decisions and validated against real invoices via
    KLSKMP_homelab/energy_analysis. Only fields sma doesn't model (Ecopower's
    own subscription/capacity/prosumer fees) are defined here.
    """

    # Fixed monthly subscription costs (EUR/month)
    ECOPOWER_SUBSCRIPTION = 5.0  # Abonnementskost

    # Fluvius data management cost (EUR/day) - Kost databeheer
    DATA_MANAGEMENT_DAILY = 0.048

    # Energy cost coefficients (based on EPEX price in EUR/MWh)
    CONSUMPTION_COEFFICIENT = CONSUMPTION_EPEX_COEFF
    CONSUMPTION_FIXED = CONSUMPTION_FIXED_EUR_KWH

    # Injection revenue coefficients (based on EPEX price in EUR/MWh)
    INJECTION_COEFFICIENT = INJECTION_EPEX_COEFF
    INJECTION_FIXED = INJECTION_FIXED_EUR_KWH

    # Distribution and other costs (EUR/kWh)
    DISTRIBUTION_TARIFF = AFNAMETARIEF_EUR_PER_KWH[HOUSEHOLD_REGION]  # Afnametarief
    INJECTION_TARIFF = 0.0017510  # Only for prosumers >10 kVA
    GSC_TARIFF = GSC_EUR_KWH  # Kost GSC
    WKK_TARIFF = WKK_EUR_KWH  # Kost WKK

    # Capacity tariff (EUR/kW/year) - Capaciteitstarief
    CAPACITY_TARIFF_YEARLY = 56.93

    # Government taxes (Heffingen)
    ENERGY_CONTRIBUTION = BIJDRAGE_ENERGIE_EUR_KWH  # Bijdrage op de energie (EUR/kWh)
    EXCISE_TAX = ACCIJNS_TIER1_EUR_KWH  # Bijzondere accijns (EUR/kWh)
    ENERGY_FUND_MONTHLY = 0.00  # Bijdrage Energiefonds (reduced rate for residential)

    @classmethod
    def calculate_fixed_cost(cls) -> float:
        """Calculate monthly fixed subscription cost (Ecopower only)"""
        return cls.ECOPOWER_SUBSCRIPTION

    @classmethod
    def calculate_data_management_cost(cls, days_in_month: int) -> float:
        """Calculate Fluvius data management cost (Kost databeheer)"""
        return cls.DATA_MANAGEMENT_DAILY * days_in_month

    @classmethod
    def calculate_energy_contribution(cls, kwh: float) -> float:
        """Calculate government energy contribution (Bijdrage op de energie)"""
        return kwh * cls.ENERGY_CONTRIBUTION

    @classmethod
    def calculate_excise_tax(cls, kwh: float) -> float:
        """Calculate excise tax (Bijzondere accijns)"""
        return kwh * cls.EXCISE_TAX

    @classmethod
    def calculate_energy_fund_contribution(cls) -> float:
        """Calculate energy fund contribution (Bijdrage Energiefonds)"""
        return cls.ENERGY_FUND_MONTHLY

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
        epex_prices: Dict[datetime, float],
        is_small_prosumer: bool = True  # ≤10 kVA, no injection tariff
    ) -> MonthlyCostBreakdown:
        """
        Calculate complete monthly cost breakdown

        Args:
            year: Year of the month
            month: Month number (1-12)
            consumption_readings: List of power consumption readings
            injection_readings: List of power injection readings
            epex_prices: Dictionary mapping timestamps to EPEX prices
            is_small_prosumer: If True (≤10 kVA), no injection tariff charged

        Returns:
            Complete monthly cost breakdown
        """
        # Get days in month for data management cost
        days_in_month = monthrange(year, month)[1]

        # Calculate energy costs and aggregate data
        energy_cost, energy_revenue, energy_data = cls.calculate_quarterly_energy_costs(
            consumption_readings,
            injection_readings,
            epex_prices
        )

        # Calculate all cost components
        fixed_cost = cls.calculate_fixed_cost()
        data_management_cost = cls.calculate_data_management_cost(days_in_month)
        distribution_cost = cls.calculate_distribution_cost(energy_data.total_kwh_delivered)

        # Injection tariff only for prosumers >10 kVA
        injection_cost = 0.0 if is_small_prosumer else cls.calculate_injection_cost(energy_data.total_kwh_returned)

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
            injection_cost=injection_cost,
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

    @classmethod
    def calculate_range_cost(
        cls,
        consumption_readings: List[PowerReading],
        injection_readings: List[PowerReading],
        epex_prices: Dict[datetime, float],
    ) -> MonthlyCostBreakdown:
        """
        Calculate energy cost for an arbitrary date range (day/week/year view).

        Excludes fixed_cost, data_management_cost and capacity_cost — those
        are inherently monthly concepts (Ecopower subscription, Fluvius daily
        fee, Fluvius capacity tariff billed on the calendar month's peak) and
        don't have a meaningful prorated value for an arbitrary sub-period.
        Use calculate_monthly_cost for a real calendar month.

        Returns:
            MonthlyCostBreakdown with year=month=0 and fixed/data_management/
            capacity costs set to 0; peak_power_kw is still populated for
            informational display, just not billed via capacity_cost here.
        """
        energy_cost, energy_revenue, energy_data = cls.calculate_quarterly_energy_costs(
            consumption_readings,
            injection_readings,
            epex_prices,
        )

        distribution_cost = cls.calculate_distribution_cost(energy_data.total_kwh_delivered)
        gsc_cost = cls.calculate_gsc_cost(energy_data.total_kwh_delivered)
        wkk_cost = cls.calculate_wkk_cost(energy_data.total_kwh_delivered)
        energy_contribution = cls.calculate_energy_contribution(energy_data.total_kwh_delivered)
        excise_tax = cls.calculate_excise_tax(energy_data.total_kwh_delivered)

        return MonthlyCostBreakdown(
            year=0,
            month=0,
            fixed_cost=0.0,
            energy_cost=energy_cost,
            energy_revenue=energy_revenue,
            distribution_cost=distribution_cost,
            injection_cost=0.0,
            gsc_cost=gsc_cost,
            wkk_cost=wkk_cost,
            capacity_cost=0.0,
            data_management_cost=0.0,
            energy_contribution=energy_contribution,
            excise_tax=excise_tax,
            energy_fund_contribution=0.0,
            total_kwh_delivered=energy_data.total_kwh_delivered,
            total_kwh_returned=energy_data.total_kwh_returned,
            peak_power_kw=energy_data.peak_power_kw,
        )
