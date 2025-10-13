"""Validate fixed tariff calculator against Ecopower website values"""
from datetime import datetime
from ecopower_tarrifs.domain.models import PowerReading
from ecopower_tarrifs.domain.fixed_tariff_calculator import FixedTariffCalculator


def create_test_readings():
    """Create test readings for validation"""
    base_time = datetime(2025, 10, 1, 0, 0, 0)

    # Example: 100 kWh consumption over a month (approx 96 readings per day for 10 days)
    # Constant 1 kW for simplicity
    consumption_readings = [
        PowerReading(
            timestamp=base_time.replace(day=1 + i // 96, hour=(i % 96) // 4, minute=(i % 4) * 15),
            power_kw=1.0
        )
        for i in range(960)  # 10 days = 240 kWh at 1 kW
    ]

    # Example: 30 kWh injection
    injection_readings = [
        PowerReading(
            timestamp=base_time.replace(day=1 + i // 96, hour=(i % 96) // 4, minute=(i % 4) * 15),
            power_kw=0.5
        )
        for i in range(288)  # 3 days at 0.5 kW = 36 kWh
    ]

    return consumption_readings, injection_readings


def validate_components():
    """Validate individual cost components against website values"""
    print("=" * 70)
    print(" VALIDATION: Fixed Tariff Calculator vs Ecopower Website")
    print("=" * 70)

    print("\n--- RATE VALIDATION ---")

    # Energy rate
    expected_energy_rate = 0.1187
    actual_energy_rate = FixedTariffCalculator.ENERGY_RATE
    print(f"Energy rate (September 2025):")
    print(f"  Expected: €{expected_energy_rate:.4f}/kWh")
    print(f"  Actual:   €{actual_energy_rate:.4f}/kWh")
    print(f"  Status:   {'✓ PASS' if expected_energy_rate == actual_energy_rate else '✗ FAIL'}")

    # GSC
    expected_gsc = 0.011
    actual_gsc = FixedTariffCalculator.GSC_TARIFF
    print(f"\nGSC (Green certificates):")
    print(f"  Expected: €{expected_gsc:.4f}/kWh")
    print(f"  Actual:   €{actual_gsc:.4f}/kWh")
    print(f"  Status:   {'✓ PASS' if expected_gsc == actual_gsc else '✗ FAIL'}")

    # WKK
    expected_wkk = 0.00392
    actual_wkk = FixedTariffCalculator.WKK_TARIFF
    print(f"\nWKK (Cogeneration):")
    print(f"  Expected: €{expected_wkk:.5f}/kWh")
    print(f"  Actual:   €{actual_wkk:.5f}/kWh")
    print(f"  Status:   {'✓ PASS' if expected_wkk == actual_wkk else '✗ FAIL'}")

    # Injection rate
    expected_injection = 0.0200
    actual_injection = -FixedTariffCalculator.INJECTION_RATE  # Negative in code
    print(f"\nInjection compensation:")
    print(f"  Expected: €{expected_injection:.4f}/kWh")
    print(f"  Actual:   €{actual_injection:.4f}/kWh")
    print(f"  Status:   {'✓ PASS' if expected_injection == actual_injection else '✗ FAIL'}")

    # Capacity tariff (analog meter)
    expected_capacity = 60.0
    actual_capacity = FixedTariffCalculator.CAPACITY_TARIFF_YEARLY
    print(f"\nCapacity tariff (analog meter):")
    print(f"  Expected: €{expected_capacity:.2f}/kVA/year")
    print(f"  Actual:   €{actual_capacity:.2f}/kW/year")
    print(f"  Note:     Website uses kVA, we use kW (equivalent for most cases)")

    # Note about Fluvius costs
    print(f"\n--- FLUVIUS COSTS (from tariff card) ---")
    print(f"Distribution tariff: €{FixedTariffCalculator.DISTRIBUTION_TARIFF:.7f}/kWh")
    print(f"Prosumer tariff: €{FixedTariffCalculator.INJECTION_TARIFF:.7f}/kWh")
    print(f"Capacity tariff: €{FixedTariffCalculator.CAPACITY_TARIFF_YEARLY:.2f}/kW/year")

    # Government taxes
    print(f"\n--- GOVERNMENT TAXES ---")
    print(f"Energy contribution: €{FixedTariffCalculator.ENERGY_CONTRIBUTION:.7f}/kWh")
    print(f"Excise tax tier 1 (0-3000 kWh): €{FixedTariffCalculator.EXCISE_TIER_1:.5f}/kWh")
    print(f"Excise tax tier 2 (3000-20000 kWh): €{FixedTariffCalculator.EXCISE_TIER_2:.5f}/kWh")
    print(f"Energy fund: €{FixedTariffCalculator.ENERGY_FUND_MONTHLY:.3f}/month")


def validate_calculation():
    """Validate a complete calculation example"""
    print("\n" + "=" * 70)
    print(" EXAMPLE CALCULATION")
    print("=" * 70)

    consumption_readings, injection_readings = create_test_readings()

    result = FixedTariffCalculator.calculate_monthly_cost(
        year=2025,
        month=10,
        consumption_readings=consumption_readings,
        injection_readings=injection_readings
    )

    print(f"\n--- Usage ---")
    print(f"Consumption: {result.total_kwh_delivered:.2f} kWh")
    print(f"Injection: {result.total_kwh_returned:.2f} kWh")
    print(f"Peak power: {result.peak_power_kw:.2f} kW")

    print(f"\n--- Cost Breakdown ---")
    print(f"Fixed cost: €{result.fixed_cost:.2f}")
    print(f"Energy cost (incl. taxes): €{result.energy_cost:.2f}")
    print(f"  - Base energy ({result.total_kwh_delivered:.2f} kWh × €0.1187): €{result.total_kwh_delivered * 0.1187:.2f}")

    energy_contribution = result.total_kwh_delivered * FixedTariffCalculator.ENERGY_CONTRIBUTION
    excise_tax = FixedTariffCalculator.calculate_excise_tax(result.total_kwh_delivered)
    print(f"  - Energy contribution: €{energy_contribution:.2f}")
    print(f"  - Excise tax: €{excise_tax:.2f}")

    print(f"Distribution cost: €{result.distribution_cost:.2f}")
    print(f"Injection cost: €{result.injection_cost:.2f}")
    print(f"GSC cost: €{result.gsc_cost:.2f}")
    print(f"WKK cost: €{result.wkk_cost:.2f}")
    print(f"Capacity cost: €{result.capacity_cost:.2f}")
    print(f"Energy revenue: €{result.energy_revenue:.2f}")

    print(f"\n--- Total ---")
    print(f"Total cost: €{result.total_cost:.2f}")

    # Manual verification
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

    print(f"\nManual verification: €{manual_total:.2f}")
    print(f"Status: {'✓ PASS' if abs(manual_total - result.total_cost) < 0.01 else '✗ FAIL'}")


def main():
    validate_components()
    validate_calculation()

    print("\n" + "=" * 70)
    print(" NOTES")
    print("=" * 70)
    print("• The fixed rate (0.1187 €/kWh) is from September 2025")
    print("• It combines 50% fixed (0.17 €/kWh) + 50% variable (Belpex)")
    print("• Government taxes are based on residential tariffs")
    print("• Capacity tariff applies to analog meters (60 €/kVA/year)")
    print("• Digital meters will use different capacity calculation")
    print("• All rates exclude VAT (6% for residential)")
    print("=" * 70)


if __name__ == "__main__":
    main()
