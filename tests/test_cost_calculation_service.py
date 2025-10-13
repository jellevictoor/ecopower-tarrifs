"""Tests for cost calculation service"""
import pytest
from datetime import datetime

from ecopower_tarrifs.services.cost_calculation_service import MonthlyCostCalculationService


class TestMonthlyCostCalculationService:
    """Test suite for MonthlyCostCalculationService"""

    def test_service_initialization(self, mock_power_repository, mock_price_repository):
        """Test service can be initialized with repositories"""
        service = MonthlyCostCalculationService(
            power_repository=mock_power_repository,
            price_repository=mock_price_repository
        )

        assert service.power_repository is mock_power_repository
        assert service.price_repository is mock_price_repository

    def test_calculate_monthly_cost(
        self,
        mock_power_repository,
        mock_price_repository
    ):
        """Test monthly cost calculation through service"""
        service = MonthlyCostCalculationService(
            power_repository=mock_power_repository,
            price_repository=mock_price_repository
        )

        result = service.calculate_monthly_cost(year=2025, month=10)

        # Verify result structure
        assert result.year == 2025
        assert result.month == 10
        assert result.fixed_cost > 0
        assert result.energy_cost > 0
        assert result.total_cost > 0

    def test_calculate_monthly_cost_with_no_data(
        self,
        mock_price_repository
    ):
        """Test monthly cost calculation with no power data"""
        from tests.conftest import MockPowerReadingRepository

        # Create empty repository
        empty_power_repo = MockPowerReadingRepository(
            consumption_data=[],
            injection_data=[]
        )

        service = MonthlyCostCalculationService(
            power_repository=empty_power_repo,
            price_repository=mock_price_repository
        )

        result = service.calculate_monthly_cost(year=2025, month=10)

        # Should still have fixed costs
        assert result.fixed_cost == 7.0
        # But no variable costs
        assert result.energy_cost == 0.0
        assert result.total_kwh_delivered == 0.0

    def test_calculate_current_month_cost(
        self,
        mock_power_repository,
        mock_price_repository
    ):
        """Test current month cost calculation"""
        service = MonthlyCostCalculationService(
            power_repository=mock_power_repository,
            price_repository=mock_price_repository
        )

        # Note: This will use current date, so the test data won't match
        # In a real scenario, you'd mock datetime.now()
        result = service.calculate_current_month_cost()

        # Just verify it returns a valid result structure
        assert result is not None
        assert result.year > 0
        assert result.month > 0
        assert result.fixed_cost == 7.0

    def test_service_uses_repository_interfaces(
        self,
        mock_power_repository,
        mock_price_repository
    ):
        """Test that service works with any repository implementation"""
        # This test verifies the ports and adapters pattern
        # Service should work with any implementation of the repository interfaces

        service = MonthlyCostCalculationService(
            power_repository=mock_power_repository,
            price_repository=mock_price_repository
        )

        # Service should successfully calculate costs
        result = service.calculate_monthly_cost(year=2025, month=10)

        assert result is not None
        assert isinstance(result.total_cost, float)

    def test_date_range_calculation(
        self,
        mock_power_repository,
        mock_price_repository
    ):
        """Test that service correctly calculates date ranges for different months"""
        service = MonthlyCostCalculationService(
            power_repository=mock_power_repository,
            price_repository=mock_price_repository
        )

        # Test regular month
        result_oct = service.calculate_monthly_cost(year=2025, month=10)
        assert result_oct.month == 10

        # Test December (edge case for year boundary)
        result_dec = service.calculate_monthly_cost(year=2025, month=12)
        assert result_dec.month == 12

    def test_integration_with_domain_calculator(
        self,
        mock_power_repository,
        mock_price_repository,
        sample_consumption_readings
    ):
        """Test that service correctly integrates with domain calculator"""
        service = MonthlyCostCalculationService(
            power_repository=mock_power_repository,
            price_repository=mock_price_repository
        )

        result = service.calculate_monthly_cost(year=2025, month=10)

        # Verify that all cost components are calculated
        assert result.fixed_cost == 7.0  # Known fixed cost
        assert result.distribution_cost > 0
        assert result.gsc_cost > 0
        assert result.wkk_cost > 0
        assert result.capacity_cost > 0

        # Verify total is sum of all components
        manual_total = (
            result.fixed_cost +
            result.energy_cost +
            result.distribution_cost +
            result.injection_cost +
            result.gsc_cost +
            result.wkk_cost +
            result.capacity_cost -
            result.energy_revenue
        )
        assert result.total_cost == pytest.approx(manual_total)
