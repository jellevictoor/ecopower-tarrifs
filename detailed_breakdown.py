"""Detailed 15-minute breakdown for verification"""
import os
from datetime import datetime
from ecopower_tarrifs.adapters.influxdb_repository import (
    InfluxDBPowerReadingRepository,
    InfluxDBEpexPriceRepository
)
from ecopower_tarrifs.domain.tariff_calculator import EcopowerTariffCalculator
from ecopower_tarrifs.domain.fixed_tariff_calculator import FixedTariffCalculator


def main():
    """Show detailed 15-minute breakdown"""

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

    try:
        # Get current month data
        now = datetime.now()
        start_date = datetime(now.year, now.month, 1)
        if now.month == 12:
            end_date = datetime(now.year + 1, 1, 1)
        else:
            end_date = datetime(now.year, now.month + 1, 1)

        # Fetch data
        consumption_readings = power_repository.get_consumption_readings(start_date, end_date)
        injection_readings = power_repository.get_injection_readings(start_date, end_date)
        epex_price_list = price_repository.get_prices(start_date, end_date)

        # Convert to dictionaries for easy lookup
        consumption_dict = {r.timestamp: r.power_kw for r in consumption_readings}
        injection_dict = {r.timestamp: r.power_kw for r in injection_readings}
        epex_dict = {p.timestamp: p.price_eur_mwh for p in epex_price_list}

        # Get all unique timestamps
        all_timestamps = sorted(set(consumption_dict.keys()) | set(injection_dict.keys()) | set(epex_dict.keys()))

        print("=" * 140)
        print(f" DETAILED 15-MINUTE BREAKDOWN - {now.year}-{now.month:02d}")
        print("=" * 140)
        print()
        print(f"{'Timestamp':<20} {'Cons(kW)':<10} {'Inj(kW)':<10} {'EPEX(€/MWh)':<13} "
              f"{'kWh15':<8} {'Dynamic€':<11} {'Fixed€':<11} {'Notes':<30}")
        print("-" * 140)

        total_dynamic_cost = 0.0
        total_fixed_cost = 0.0
        total_dynamic_revenue = 0.0
        total_fixed_revenue = 0.0
        total_kwh_consumed = 0.0
        total_kwh_injected = 0.0
        max_power = 0.0

        # Filter to intervals with actual data
        intervals_with_data = []
        for ts in all_timestamps:
            consumption_kw = consumption_dict.get(ts, 0.0)
            injection_kw = injection_dict.get(ts, 0.0)
            if consumption_kw > 0 or injection_kw > 0:
                intervals_with_data.append(ts)

        # Show all intervals (or set limit if too many)
        sample_size = len(intervals_with_data)  # Show all data
        # sample_size = min(100, len(intervals_with_data))  # Uncomment to limit

        for i, ts in enumerate(intervals_with_data[:sample_size]):
            consumption_kw = consumption_dict.get(ts, 0.0)
            injection_kw = injection_dict.get(ts, 0.0)
            epex_price = epex_dict.get(ts, 0.0)

            # Calculate kWh for this 15-minute period
            kwh_consumed = consumption_kw * 0.25
            kwh_injected = injection_kw * 0.25

            total_kwh_consumed += kwh_consumed
            total_kwh_injected += kwh_injected

            if consumption_kw > max_power:
                max_power = consumption_kw

            # Dynamic tariff calculation
            dynamic_cost_per_kwh = EcopowerTariffCalculator.calculate_energy_cost_per_kwh(epex_price)
            dynamic_revenue_per_kwh = EcopowerTariffCalculator.calculate_energy_revenue_per_kwh(epex_price)

            dynamic_cost_15m = dynamic_cost_per_kwh * kwh_consumed
            dynamic_revenue_15m = dynamic_revenue_per_kwh * kwh_injected

            total_dynamic_cost += dynamic_cost_15m
            total_dynamic_revenue += dynamic_revenue_15m

            # Fixed tariff calculation
            fixed_cost_per_kwh = 0.1187  # Base energy rate only for display
            fixed_revenue_per_kwh = 0.0200

            fixed_cost_15m = fixed_cost_per_kwh * kwh_consumed
            fixed_revenue_15m = fixed_revenue_per_kwh * kwh_injected

            total_fixed_cost += fixed_cost_15m
            total_fixed_revenue += fixed_revenue_15m

            # Determine notes
            notes = []
            if epex_price == 0:
                notes.append("NO EPEX DATA")
            if consumption_kw == 0 and injection_kw == 0:
                notes.append("NO POWER DATA")
            if consumption_kw > 4:
                notes.append("HIGH LOAD")

            note_str = ", ".join(notes) if notes else ""

            # Calculate net for this period
            net_dynamic = dynamic_cost_15m - dynamic_revenue_15m
            net_fixed = fixed_cost_15m - fixed_revenue_15m

            # Show consumption line
            if kwh_consumed > 0:
                print(f"{ts.strftime('%Y-%m-%d %H:%M'):<20} "
                      f"{consumption_kw:>8.3f}   "
                      f"{'-':>8}   "
                      f"{epex_price:>11.2f}  "
                      f"{kwh_consumed:>6.3f}   "
                      f"€{dynamic_cost_15m:>8.4f}  "
                      f"€{fixed_cost_15m:>8.4f}  "
                      f"{note_str:<30}")

            # Show injection line (if any)
            if kwh_injected > 0:
                print(f"{ts.strftime('%Y-%m-%d %H:%M'):<20} "
                      f"{'-':>8}   "
                      f"{injection_kw:>8.3f}   "
                      f"{epex_price:>11.2f}  "
                      f"{kwh_injected:>6.3f}   "
                      f"€{-dynamic_revenue_15m:>8.4f}  "
                      f"€{-fixed_revenue_15m:>8.4f}  "
                      f"INJECTION")

        print("-" * 140)
        print(f"\n{'SAMPLE TOTALS (first 50 intervals)':<54} "
              f"{total_kwh_consumed:>6.2f}   "
              f"€{total_dynamic_cost:>8.2f}  "
              f"€{total_fixed_cost:>8.2f}")
        print(f"{'INJECTION REVENUE':<54} "
              f"{total_kwh_injected:>6.2f}   "
              f"€{total_dynamic_revenue:>8.2f}  "
              f"€{total_fixed_revenue:>8.2f}")

        print("\n" + "=" * 140)
        print(" CALCULATION FORMULAS")
        print("=" * 140)
        print("\nDYNAMIC TARIFF:")
        print(f"  Cost per kWh   = 0.00102 × EPEX(€/MWh) + 0.004")
        print(f"  Revenue per kWh = 0.00098 × EPEX(€/MWh) - 0.015")
        print(f"  Example @ 75 €/MWh:")
        print(f"    Cost   = 0.00102 × 75 + 0.004 = €{0.00102 * 75 + 0.004:.4f}/kWh")
        print(f"    Revenue = 0.00098 × 75 - 0.015 = €{0.00098 * 75 - 0.015:.4f}/kWh")

        print("\nFIXED TARIFF:")
        print(f"  Cost per kWh = €0.1187 (base) + €0.0019261 (energy contrib) + excise tax")
        print(f"  Revenue per kWh = €0.0200")
        print(f"  Note: Excise tax is tiered based on total monthly consumption")

        print("\nPER 15-MINUTE CALCULATION:")
        print(f"  kWh in 15 min = Power(kW) × 0.25")
        print(f"  Cost for period = kWh × Cost per kWh")
        print(f"  Revenue for period = kWh × Revenue per kWh")

        print("\n" + "=" * 140)
        print(" FULL MONTH SUMMARY")
        print("=" * 140)
        print(f"Total intervals: {len(all_timestamps)}")
        print(f"Sample shown: {sample_size} intervals")
        print(f"Total consumption: {sum(consumption_dict.values()) * 0.25:.2f} kWh")
        print(f"Total injection: {sum(injection_dict.values()) * 0.25:.2f} kWh")
        print(f"Peak power: {max(consumption_dict.values()):.2f} kW")
        print(f"EPEX prices available: {len(epex_dict)} intervals")
        print(f"Average EPEX price: {sum(epex_dict.values()) / len(epex_dict) if epex_dict else 0:.2f} €/MWh")

        print("\n" + "=" * 140)
        print(" VERIFICATION TIPS")
        print("=" * 140)
        print("1. Check timestamps align: Consumption, Injection, and EPEX should match")
        print("2. Verify EPEX prices are reasonable (typically 30-200 €/MWh)")
        print("3. Check 'NO EPEX DATA' warnings - these default to 0 and reduce costs")
        print("4. Spot-check: Pick a timestamp, verify kWh calculation and rate formula")
        print("5. Note: Fixed tariff also includes government taxes not shown per-interval")
        print("=" * 140)

    finally:
        power_repository.close()
        price_repository.close()


if __name__ == "__main__":
    main()
