"""Compare dynamic EPEX pricing vs fixed tariff"""
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
from ecopower_tarrifs.adapters.influxdb_repository import (
    InfluxDBPowerReadingRepository,
    InfluxDBEpexPriceRepository
)
from ecopower_tarrifs.services.cost_calculation_service import MonthlyCostCalculationService
from ecopower_tarrifs.services.fixed_cost_calculation_service import FixedMonthlyCostCalculationService


def get_target_month() -> tuple[int, int]:
    """Get target year and month based on TARGET_MONTH env var.

    Returns:
        Tuple of (year, month)
    """
    target = os.getenv("TARGET_MONTH", "current").lower()
    now = datetime.now()

    if target == "previous":
        prev = now - relativedelta(months=1)
        return prev.year, prev.month
    else:
        return now.year, now.month


def main():
    """Compare monthly electricity cost between both tariff types"""

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

    # Initialize services
    dynamic_service = MonthlyCostCalculationService(
        power_repository=power_repository,
        price_repository=price_repository
    )

    fixed_service = FixedMonthlyCostCalculationService(
        power_repository=power_repository
    )

    try:
        # Get target month (current or previous based on TARGET_MONTH env var)
        year, month = get_target_month()

        # Calculate cost for target month with both tariffs
        dynamic_result = dynamic_service.calculate_monthly_cost(year, month)
        fixed_result = fixed_service.calculate_monthly_cost(year, month)

        # Print comparison
        print("\n" + "=" * 70)
        print(" TARIFF COMPARISON: Dynamic EPEX vs Fixed Rate")
        print("=" * 70)
        print(f"Month: {dynamic_result.year}-{dynamic_result.month:02d}")

        print(f"\n{'─' * 70}")
        print(f"{'USAGE METRICS':<50}")
        print(f"{'─' * 70}")
        print(f"{'Consumption:':<35} {dynamic_result.total_kwh_delivered:>10.2f} kWh")
        print(f"{'Injection:':<35} {dynamic_result.total_kwh_returned:>10.2f} kWh")
        print(f"{'Peak power:':<35} {dynamic_result.peak_power_kw:>10.2f} kW")

        print(f"\n{'─' * 70}")
        print(f"{'COST BREAKDOWN':<35} {'DYNAMIC':<17} {'FIXED':<17}")
        print(f"{'─' * 70}")
        print(f"{'Abonnementskost':<35} €{dynamic_result.fixed_cost:>8.2f}        €{fixed_result.fixed_cost:>8.2f}")
        print(f"{'Energy cost':<35} €{dynamic_result.energy_cost:>8.2f}        €{fixed_result.energy_cost:>8.2f}")
        print(f"{'GSC cost':<35} €{dynamic_result.gsc_cost:>8.2f}        €{fixed_result.gsc_cost:>8.2f}")
        print(f"{'WKK cost':<35} €{dynamic_result.wkk_cost:>8.2f}        €{fixed_result.wkk_cost:>8.2f}")
        print(f"\n{'NETTARIEVEN (Fluvius)':<35}")
        print(f"{'Kost databeheer':<35} €{dynamic_result.data_management_cost:>8.2f}        €{fixed_result.data_management_cost:>8.2f}")
        print(f"{'Capaciteitstarief':<35} €{dynamic_result.capacity_cost:>8.2f}        €{fixed_result.capacity_cost:>8.2f}")
        print(f"{'Afnametarief':<35} €{dynamic_result.distribution_cost:>8.2f}        €{fixed_result.distribution_cost:>8.2f}")
        print(f"{'Injectietarief':<35} €{dynamic_result.injection_cost:>8.2f}        €{fixed_result.injection_cost:>8.2f}")
        print(f"\n{'HEFFINGEN (Government)':<35}")
        print(f"{'Bijdrage op de energie':<35} €{dynamic_result.energy_contribution:>8.2f}        €{fixed_result.energy_contribution:>8.2f}")
        print(f"{'Bijzondere accijns':<35} €{dynamic_result.excise_tax:>8.2f}        €{fixed_result.excise_tax:>8.2f}")
        print(f"{'Bijdrage Energiefonds':<35} €{dynamic_result.energy_fund_contribution:>8.2f}        €{fixed_result.energy_fund_contribution:>8.2f}")

        print(f"\n{'─' * 70}")
        print(f"{'REVENUE':<35} {'DYNAMIC':<17} {'FIXED':<17}")
        print(f"{'─' * 70}")
        print(f"{'Energy revenue':<35} €{dynamic_result.energy_revenue:>8.2f}        €{fixed_result.energy_revenue:>8.2f}")

        print(f"\n{'═' * 70}")
        print(f"{'TOTAL COST':<35} €{dynamic_result.total_cost:>8.2f}        €{fixed_result.total_cost:>8.2f}")
        print(f"{'═' * 70}")

        print(f"\n{'─' * 70}")
        print(f"{'AVERAGE PRICE PER KWH':<35} {'DYNAMIC':<17} {'FIXED':<17}")
        print(f"{'─' * 70}")
        print(f"{'Ex VAT:':<35} €{dynamic_result.average_price_per_kwh_ex_vat:>8.4f}        €{fixed_result.average_price_per_kwh_ex_vat:>8.4f}")
        print(f"{'Incl VAT (6%):':<35} €{dynamic_result.average_price_per_kwh_incl_vat:>8.4f}        €{fixed_result.average_price_per_kwh_incl_vat:>8.4f}")

        # Calculate difference
        difference = fixed_result.total_cost - dynamic_result.total_cost
        percentage = (difference / dynamic_result.total_cost) * 100

        print(f"\n{'─' * 70}")
        print(f"{'COMPARISON':<50}")
        print(f"{'─' * 70}")
        if difference > 0:
            print(f"Fixed tariff is €{abs(difference):.2f} MORE expensive ({percentage:+.1f}%)")
            print(f"💡 Dynamic EPEX pricing saves you €{abs(difference):.2f} this month!")
        elif difference < 0:
            print(f"Fixed tariff is €{abs(difference):.2f} CHEAPER ({percentage:.1f}%)")
            print(f"💡 Fixed tariff saves you €{abs(difference):.2f} this month!")
        else:
            print("Both tariffs cost exactly the same this month")

        # Additional insights
        avg_epex = dynamic_result.energy_cost / dynamic_result.total_kwh_delivered if dynamic_result.total_kwh_delivered > 0 else 0
        fixed_rate = 0.1187
        print(f"\n{'─' * 70}")
        print(f"{'INSIGHTS':<50}")
        print(f"{'─' * 70}")
        print(f"Average dynamic rate this month: €{avg_epex:.4f}/kWh")
        print(f"Fixed rate: €{fixed_rate:.4f}/kWh")
        print(f"Difference: €{avg_epex - fixed_rate:.4f}/kWh")

    finally:
        # Clean up connections
        power_repository.close()
        price_repository.close()


if __name__ == "__main__":
    main()
