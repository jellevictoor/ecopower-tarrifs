"""Example usage of the ecopower tariff calculator"""
import os
from ecopower_tarrifs.adapters.influxdb_repository import (
    InfluxDBPowerReadingRepository,
    InfluxDBEpexPriceRepository
)
from ecopower_tarrifs.services.cost_calculation_service import MonthlyCostCalculationService


def main():
    """Calculate current month's electricity cost"""

    # Configuration from environment variables
    INFLUXDB_HOST = os.getenv("INFLUXDB_HOST", "192.168.1.5")
    INFLUXDB_PORT = int(os.getenv("INFLUXDB_PORT", "8086"))
    INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "")
    INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "victoor.io")
    METERING_BUCKET = os.getenv("METERING_BUCKET", "metering")
    PRICES_BUCKET = os.getenv("PRICES_BUCKET", "energy_prices")

    # Initialize repositories (adapters)
    power_repository = InfluxDBPowerReadingRepository(
        host=INFLUXDB_HOST,
        port=INFLUXDB_PORT,
        token=INFLUXDB_TOKEN,
        org=INFLUXDB_ORG,
        bucket=METERING_BUCKET
    )

    price_repository = InfluxDBEpexPriceRepository(
        host=INFLUXDB_HOST,
        port=INFLUXDB_PORT,
        token=INFLUXDB_TOKEN,
        org=INFLUXDB_ORG,
        bucket=PRICES_BUCKET
    )

    # Initialize service
    service = MonthlyCostCalculationService(
        power_repository=power_repository,
        price_repository=price_repository
    )

    try:
        # Calculate current month's cost
        result = service.calculate_current_month_cost()

        # Print results
        print(f"\n=== Ecopower Tariff Calculation ===")
        print(f"Month: {result.year}-{result.month:02d}")
        print(f"\n--- Usage ---")
        print(f"Consumption: {result.total_kwh_delivered:.2f} kWh")
        print(f"Injection: {result.total_kwh_returned:.2f} kWh")
        print(f"Peak power: {result.peak_power_kw:.2f} kW")
        print(f"\n--- Costs ---")
        print(f"Fixed cost: €{result.fixed_cost:.2f}")
        print(f"Energy cost: €{result.energy_cost:.2f}")
        print(f"Distribution cost: €{result.distribution_cost:.2f}")
        print(f"Injection cost: €{result.injection_cost:.2f}")
        print(f"GSC cost: €{result.gsc_cost:.2f}")
        print(f"WKK cost: €{result.wkk_cost:.2f}")
        print(f"Capacity cost: €{result.capacity_cost:.2f}")
        print(f"\n--- Revenue ---")
        print(f"Energy revenue: €{result.energy_revenue:.2f}")
        print(f"\n--- Total ---")
        print(f"Total cost: €{result.total_cost:.2f}")

    finally:
        # Clean up connections
        power_repository.close()
        price_repository.close()


def calculate_specific_month(year: int, month: int):
    """Calculate cost for a specific month"""

    # Configuration from environment variables
    INFLUXDB_HOST = os.getenv("INFLUXDB_HOST", "192.168.1.5")
    INFLUXDB_PORT = int(os.getenv("INFLUXDB_PORT", "8086"))
    INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "")
    INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "victoor.io")
    METERING_BUCKET = os.getenv("METERING_BUCKET", "metering")
    PRICES_BUCKET = os.getenv("PRICES_BUCKET", "energy_prices")

    # Initialize repositories
    power_repository = InfluxDBPowerReadingRepository(
        host=INFLUXDB_HOST,
        port=INFLUXDB_PORT,
        token=INFLUXDB_TOKEN,
        org=INFLUXDB_ORG,
        bucket=METERING_BUCKET
    )

    price_repository = InfluxDBEpexPriceRepository(
        host=INFLUXDB_HOST,
        port=INFLUXDB_PORT,
        token=INFLUXDB_TOKEN,
        org=INFLUXDB_ORG,
        bucket=PRICES_BUCKET
    )

    # Initialize service
    service = MonthlyCostCalculationService(
        power_repository=power_repository,
        price_repository=price_repository
    )

    try:
        # Calculate specific month's cost
        result = service.calculate_monthly_cost(year=year, month=month)
        return result
    finally:
        # Clean up connections
        power_repository.close()
        price_repository.close()


if __name__ == "__main__":
    main()
