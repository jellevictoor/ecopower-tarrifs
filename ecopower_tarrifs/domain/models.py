"""Domain models for ecopower tariff calculations"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class PowerReading:
    """Represents a power reading at a specific time"""
    timestamp: datetime
    power_kw: float  # Power in kilowatts


@dataclass(frozen=True)
class EpexPrice:
    """Represents an EPEX day-ahead price"""
    timestamp: datetime
    price_eur_mwh: float  # Price in EUR/MWh


@dataclass(frozen=True)
class MonthlyEnergyData:
    """Aggregated energy data for a month"""
    total_kwh_delivered: float
    total_kwh_returned: float
    peak_power_kw: float


@dataclass(frozen=True)
class MonthlyCostBreakdown:
    """Complete breakdown of monthly costs"""
    year: int
    month: int

    # Cost components
    fixed_cost: float
    energy_cost: float
    energy_revenue: float
    distribution_cost: float
    injection_cost: float
    gsc_cost: float
    wkk_cost: float
    capacity_cost: float

    # Usage metrics
    total_kwh_delivered: float
    total_kwh_returned: float
    peak_power_kw: float

    @property
    def total_cost(self) -> float:
        """Calculate total cost (costs - revenue)"""
        return (
            self.fixed_cost +
            self.energy_cost +
            self.distribution_cost +
            self.injection_cost +
            self.gsc_cost +
            self.wkk_cost +
            self.capacity_cost -
            self.energy_revenue
        )

    @property
    def average_price_per_kwh_ex_vat(self) -> float:
        """Calculate average price per kWh excluding VAT"""
        if self.total_kwh_delivered == 0:
            return 0.0
        return self.total_cost / self.total_kwh_delivered

    @property
    def average_price_per_kwh_incl_vat(self) -> float:
        """Calculate average price per kWh including VAT (6% for residential)"""
        if self.total_kwh_delivered == 0:
            return 0.0
        return (self.total_cost * 1.06) / self.total_kwh_delivered
