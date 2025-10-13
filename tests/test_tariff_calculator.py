"""Tests for tariff calculator domain logic"""
import pytest
from datetime import datetime

from ecopower_tarrifs.domain.tariff_calculator import EcopowerTariffCalculator
from ecopower_tarrifs.domain.models import PowerReading, EpexPrice


class TestEcopowerTariffCalculator:
    """Test suite for EcopowerTariffCalculator"""

    def test_calculate_fixed_cost(self):
        """Test fixed monthly cost calculation"""
        result = EcopowerTariffCalculator.calculate_fixed_cost()
        assert result == 7.0  # 5 (ecopower) + 2 (fluvius)

    def test_calculate_energy_cost_per_kwh(self):
        """Test energy cost calculation based on EPEX price"""
        epex_price = 100.0  # EUR/MWh
        result = EcopowerTariffCalculator.calculate_energy_cost_per_kwh(epex_price)
        expected = 0.00102 * 100.0 + 0.004
        assert result == pytest.approx(expected)

    def test_calculate_energy_revenue_per_kwh(self):
        """Test energy injection revenue calculation"""
        epex_price = 100.0  # EUR/MWh
        result = EcopowerTariffCalculator.calculate_energy_revenue_per_kwh(epex_price)
        expected = 0.00098 * 100.0 - 0.015
        assert result == pytest.approx(expected)

    def test_calculate_distribution_cost(self):
        """Test distribution cost calculation"""
        kwh = 100.0
        result = EcopowerTariffCalculator.calculate_distribution_cost(kwh)
        expected = 100.0 * 0.0704386
        assert result == pytest.approx(expected)

    def test_calculate_injection_cost(self):
        """Test injection tariff calculation"""
        kwh = 50.0
        result = EcopowerTariffCalculator.calculate_injection_cost(kwh)
        expected = 50.0 * 0.0017510
        assert result == pytest.approx(expected)

    def test_calculate_gsc_cost(self):
        """Test GSC cost calculation"""
        kwh = 100.0
        result = EcopowerTariffCalculator.calculate_gsc_cost(kwh)
        expected = 100.0 * 0.011
        assert result == pytest.approx(expected)

    def test_calculate_wkk_cost(self):
        """Test WKK cost calculation"""
        kwh = 100.0
        result = EcopowerTariffCalculator.calculate_wkk_cost(kwh)
        expected = 100.0 * 0.00392
        assert result == pytest.approx(expected)

    def test_calculate_monthly_capacity_cost(self):
        """Test monthly capacity tariff calculation"""
        peak_kw = 5.0
        result = EcopowerTariffCalculator.calculate_monthly_capacity_cost(peak_kw)
        expected = (5.0 * 56.93) / 12
        assert result == pytest.approx(expected)

    def test_calculate_quarterly_energy_costs_with_sample_data(
        self,
        sample_consumption_readings,
        sample_injection_readings,
        sample_epex_prices
    ):
        """Test energy cost calculation with sample data"""
        # Convert EPEX prices to dictionary
        epex_prices = {p.timestamp: p.price_eur_mwh for p in sample_epex_prices}

        energy_cost, energy_revenue, energy_data = (
            EcopowerTariffCalculator.calculate_quarterly_energy_costs(
                consumption_readings=sample_consumption_readings,
                injection_readings=sample_injection_readings,
                epex_prices=epex_prices
            )
        )

        # Verify results are positive
        assert energy_cost > 0
        assert energy_revenue > 0
        assert energy_data.total_kwh_delivered > 0
        assert energy_data.total_kwh_returned > 0
        assert energy_data.peak_power_kw > 0

    def test_calculate_monthly_cost_complete(
        self,
        sample_consumption_readings,
        sample_injection_readings,
        sample_epex_prices
    ):
        """Test complete monthly cost calculation"""
        epex_prices = {p.timestamp: p.price_eur_mwh for p in sample_epex_prices}

        result = EcopowerTariffCalculator.calculate_monthly_cost(
            year=2025,
            month=10,
            consumption_readings=sample_consumption_readings,
            injection_readings=sample_injection_readings,
            epex_prices=epex_prices
        )

        # Verify all components are present
        assert result.year == 2025
        assert result.month == 10
        assert result.fixed_cost == 7.0
        assert result.energy_cost > 0
        assert result.energy_revenue > 0
        assert result.distribution_cost > 0
        assert result.injection_cost > 0
        assert result.gsc_cost > 0
        assert result.wkk_cost > 0
        assert result.capacity_cost > 0
        assert result.total_cost > 0

    def test_monthly_cost_breakdown_total_property(self):
        """Test that MonthlyCostBreakdown.total_cost property calculates correctly"""
        from ecopower_tarrifs.domain.models import MonthlyCostBreakdown

        breakdown = MonthlyCostBreakdown(
            year=2025,
            month=10,
            fixed_cost=10.0,
            energy_cost=20.0,
            energy_revenue=5.0,
            distribution_cost=15.0,
            injection_cost=3.0,
            gsc_cost=4.0,
            wkk_cost=2.0,
            capacity_cost=8.0,
            total_kwh_delivered=100.0,
            total_kwh_returned=50.0,
            peak_power_kw=5.0
        )

        expected_total = 10 + 20 + 15 + 3 + 4 + 2 + 8 - 5
        assert breakdown.total_cost == pytest.approx(expected_total)

    def test_energy_cost_increases_with_epex_price(self):
        """Test that energy cost increases with EPEX price"""
        low_price = 50.0
        high_price = 150.0

        low_cost = EcopowerTariffCalculator.calculate_energy_cost_per_kwh(low_price)
        high_cost = EcopowerTariffCalculator.calculate_energy_cost_per_kwh(high_price)

        assert high_cost > low_cost

    def test_energy_revenue_increases_with_epex_price(self):
        """Test that injection revenue increases with EPEX price"""
        low_price = 50.0
        high_price = 150.0

        low_revenue = EcopowerTariffCalculator.calculate_energy_revenue_per_kwh(low_price)
        high_revenue = EcopowerTariffCalculator.calculate_energy_revenue_per_kwh(high_price)

        assert high_revenue > low_revenue
