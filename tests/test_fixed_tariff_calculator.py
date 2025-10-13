"""Tests for fixed tariff calculator"""
import pytest
from datetime import datetime

from ecopower_tarrifs.domain.fixed_tariff_calculator import FixedTariffCalculator
from ecopower_tarrifs.domain.models import PowerReading


class TestFixedTariffCalculator:
    """Test suite for FixedTariffCalculator"""

    def test_calculate_fixed_cost(self):
        """Test fixed monthly cost calculation"""
        result = FixedTariffCalculator.calculate_fixed_cost()
        # 5 (ecopower) + 2 (fluvius) + 0.005 (energy fund)
        assert result == pytest.approx(7.005)

    def test_calculate_energy_cost(self):
        """Test fixed energy cost calculation"""
        kwh = 100.0
        result = FixedTariffCalculator.calculate_energy_cost(kwh)
        expected = 100.0 * 0.1187
        assert result == pytest.approx(expected)

    def test_calculate_energy_revenue(self):
        """Test fixed injection revenue calculation"""
        kwh = 50.0
        result = FixedTariffCalculator.calculate_energy_revenue(kwh)
        expected = 50.0 * 0.0200  # Positive revenue
        assert result == pytest.approx(expected)

    def test_calculate_excise_tax_tier_1(self):
        """Test excise tax for tier 1 (0-3000 kWh)"""
        kwh = 1000.0
        result = FixedTariffCalculator.calculate_excise_tax(kwh)
        expected = 1000.0 * 0.04748
        assert result == pytest.approx(expected)

    def test_calculate_excise_tax_tier_2(self):
        """Test excise tax for tier 2 (3000-20000 kWh)"""
        kwh = 5000.0
        result = FixedTariffCalculator.calculate_excise_tax(kwh)
        expected = (
            3000 * 0.04748 +  # First 3000 kWh
            2000 * 0.04748    # Next 2000 kWh
        )
        assert result == pytest.approx(expected)

    def test_calculate_excise_tax_tier_3(self):
        """Test excise tax for tier 3 (20000-50000 kWh)"""
        kwh = 25000.0
        result = FixedTariffCalculator.calculate_excise_tax(kwh)
        expected = (
            3000 * 0.04748 +   # First 3000 kWh
            17000 * 0.04748 +  # Next 17000 kWh (3000-20000)
            5000 * 0.04546     # Next 5000 kWh (20000-25000)
        )
        assert result == pytest.approx(expected)

    def test_calculate_excise_tax_tier_4(self):
        """Test excise tax for tier 4 (50000+ kWh)"""
        kwh = 60000.0
        result = FixedTariffCalculator.calculate_excise_tax(kwh)
        expected = (
            3000 * 0.04748 +   # First 3000 kWh
            17000 * 0.04748 +  # Next 17000 kWh
            30000 * 0.04546 +  # Next 30000 kWh
            10000 * 0.04478    # Next 10000 kWh
        )
        assert result == pytest.approx(expected)

    def test_calculate_energy_contribution(self):
        """Test government energy contribution"""
        kwh = 100.0
        result = FixedTariffCalculator.calculate_energy_contribution(kwh)
        expected = 100.0 * 0.0019261
        assert result == pytest.approx(expected)

    def test_calculate_distribution_cost(self):
        """Test distribution cost calculation"""
        kwh = 100.0
        result = FixedTariffCalculator.calculate_distribution_cost(kwh)
        expected = 100.0 * 0.0704386
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
        assert result.fixed_cost == pytest.approx(7.005)
        assert result.energy_cost > 0
        assert result.energy_revenue > 0
        assert result.distribution_cost > 0
        assert result.injection_cost > 0
        assert result.gsc_cost > 0
        assert result.wkk_cost > 0
        assert result.capacity_cost > 0
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
        """Test that monthly cost includes energy contribution and excise tax"""
        result = FixedTariffCalculator.calculate_monthly_cost(
            year=2025,
            month=10,
            consumption_readings=sample_consumption_readings,
            injection_readings=sample_injection_readings
        )

        # Energy cost should include base rate + contribution + excise
        energy_data = FixedTariffCalculator.aggregate_energy_data(
            sample_consumption_readings,
            sample_injection_readings
        )

        base_energy = energy_data.total_kwh_delivered * 0.1187
        contribution = energy_data.total_kwh_delivered * 0.0019261
        excise = FixedTariffCalculator.calculate_excise_tax(energy_data.total_kwh_delivered)

        expected_energy_cost = base_energy + contribution + excise
        assert result.energy_cost == pytest.approx(expected_energy_cost)
