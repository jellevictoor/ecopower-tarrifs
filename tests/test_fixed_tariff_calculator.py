"""Tests for fixed tariff calculator"""
import pytest
from datetime import datetime

from ecopower_tarrifs.domain.fixed_tariff_calculator import FixedTariffCalculator
from ecopower_tarrifs.domain.models import PowerReading


class TestFixedTariffCalculator:
    """Test suite for FixedTariffCalculator"""

    def test_calculate_fixed_cost(self):
        """Test fixed monthly cost calculation (Abonnementskost only)"""
        result = FixedTariffCalculator.calculate_fixed_cost()
        assert result == pytest.approx(5.0)  # Ecopower subscription only

    def test_calculate_energy_cost(self):
        """Test fixed energy cost calculation"""
        kwh = 100.0
        result = FixedTariffCalculator.calculate_energy_cost(kwh)
        expected = 100.0 * 0.1298  # Updated fixed rate
        assert result == pytest.approx(expected)

    def test_calculate_energy_revenue(self):
        """Test fixed injection revenue calculation"""
        kwh = 50.0
        result = FixedTariffCalculator.calculate_energy_revenue(kwh)
        expected = 50.0 * 0.0200  # Positive revenue
        assert result == pytest.approx(expected)

    def test_calculate_excise_tax(self):
        """Test excise tax (Bijzondere accijns, residential tier 1)"""
        kwh = 1000.0
        result = FixedTariffCalculator.calculate_excise_tax(kwh)
        expected = 1000.0 * 0.04748
        assert result == pytest.approx(expected)

    def test_calculate_energy_contribution(self):
        """Test government energy contribution (Bijdrage op de energie)"""
        kwh = 100.0
        result = FixedTariffCalculator.calculate_energy_contribution(kwh)
        expected = 100.0 * 0.0019261
        assert result == pytest.approx(expected)

    def test_calculate_distribution_cost(self):
        """Test distribution cost calculation (Afnametarief, Fluvius West)"""
        kwh = 100.0
        result = FixedTariffCalculator.calculate_distribution_cost(kwh)
        expected = 100.0 * 0.0631937
        assert result == pytest.approx(expected)

    def test_calculate_monthly_capacity_cost(self):
        """Test monthly capacity tariff calculation"""
        peak_kw = 5.0
        result = FixedTariffCalculator.calculate_monthly_capacity_cost(peak_kw)
        expected = (5.0 * 56.93) / 12
        assert result == pytest.approx(expected)

    def test_aggregate_energy_data(
        self,
        sample_consumption_readings,
        sample_injection_readings
    ):
        """Test energy data aggregation"""
        energy_data = FixedTariffCalculator.aggregate_energy_data(
            consumption_readings=sample_consumption_readings,
            injection_readings=sample_injection_readings
        )

        assert energy_data.total_kwh_delivered > 0
        assert energy_data.total_kwh_returned > 0
        assert energy_data.peak_power_kw > 0

    def test_calculate_monthly_cost_complete(
        self,
        sample_consumption_readings,
        sample_injection_readings
    ):
        """Test complete monthly cost calculation with fixed tariff"""
        result = FixedTariffCalculator.calculate_monthly_cost(
            year=2025,
            month=10,
            consumption_readings=sample_consumption_readings,
            injection_readings=sample_injection_readings
        )

        # Verify all components are present
        assert result.year == 2025
        assert result.month == 10
        assert result.fixed_cost == pytest.approx(5.0)  # Abonnementskost only
        assert result.energy_cost > 0
        assert result.energy_revenue > 0
        assert result.distribution_cost > 0
        assert result.injection_cost == 0.0  # Small prosumer, no injection tariff
        assert result.gsc_cost > 0
        assert result.wkk_cost > 0
        assert result.capacity_cost > 0
        assert result.data_management_cost > 0  # Kost databeheer
        assert result.energy_contribution > 0  # Bijdrage op de energie
        assert result.excise_tax > 0  # Bijzondere accijns
        assert result.total_cost > 0

    def test_fixed_tariff_no_epex_dependency(
        self,
        sample_consumption_readings,
        sample_injection_readings
    ):
        """Test that fixed tariff calculator doesn't need EPEX prices"""
        # Should work with just power readings, no EPEX prices needed
        result = FixedTariffCalculator.calculate_monthly_cost(
            year=2025,
            month=10,
            consumption_readings=sample_consumption_readings,
            injection_readings=sample_injection_readings
        )

        # Should produce valid results
        assert result.total_cost > 0
        assert result.energy_cost > 0

    def test_energy_cost_is_fixed_rate(self):
        """Test that energy cost uses fixed rate, not variable"""
        kwh_1 = 100.0
        kwh_2 = 200.0

        cost_1 = FixedTariffCalculator.calculate_energy_cost(kwh_1)
        cost_2 = FixedTariffCalculator.calculate_energy_cost(kwh_2)

        # Should be exactly proportional (fixed rate)
        assert cost_2 == pytest.approx(cost_1 * 2)

    def test_injection_revenue_is_positive(self):
        """Test that injection revenue is positive (you get paid)"""
        kwh = 50.0
        revenue = FixedTariffCalculator.calculate_energy_revenue(kwh)
        assert revenue > 0  # You receive money

    def test_monthly_cost_includes_all_taxes(
        self,
        sample_consumption_readings,
        sample_injection_readings
    ):
        """Test that monthly cost includes separate energy contribution and excise tax"""
        result = FixedTariffCalculator.calculate_monthly_cost(
            year=2025,
            month=10,
            consumption_readings=sample_consumption_readings,
            injection_readings=sample_injection_readings
        )

        # Verify taxes are tracked separately (not combined into energy_cost)
        energy_data = FixedTariffCalculator.aggregate_energy_data(
            sample_consumption_readings,
            sample_injection_readings
        )

        expected_energy_cost = energy_data.total_kwh_delivered * 0.1298  # Base rate only
        expected_contribution = energy_data.total_kwh_delivered * 0.0019261
        expected_excise = energy_data.total_kwh_delivered * 0.04748

        assert result.energy_cost == pytest.approx(expected_energy_cost)
        assert result.energy_contribution == pytest.approx(expected_contribution)
        assert result.excise_tax == pytest.approx(expected_excise)
