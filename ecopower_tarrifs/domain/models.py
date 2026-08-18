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
    fixed_cost: float  # Abonnementskost (Ecopower subscription)
    energy_cost: float  # Dynamische burgerstroom energy
    energy_revenue: float  # Injection revenue
    distribution_cost: float  # Afnametarief
    injection_cost: float  # Injectietarief (€0 for ≤10 kVA)
    gsc_cost: float  # Kost GSC
    wkk_cost: float  # Kost WKK
    capacity_cost: float  # Capaciteitstarief

    # Fluvius costs
    data_management_cost: float = 0.0  # Kost databeheer (€0.048/day)

    # Government taxes (Heffingen)
    energy_contribution: float = 0.0  # Bijdrage op de energie
    excise_tax: float = 0.0  # Bijzondere accijns
    energy_fund_contribution: float = 0.0  # Bijdrage Energiefonds

    # Usage metrics
    total_kwh_delivered: float = 0.0
    total_kwh_returned: float = 0.0
    peak_power_kw: float = 0.0

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
            self.capacity_cost +
            self.data_management_cost +
            self.energy_contribution +
            self.excise_tax +
            self.energy_fund_contribution -
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
