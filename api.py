"""Minimal HTTP API exposing the monthly cost calculation as JSON.

Lets other consumers (e.g. klskmp-energy-dashboard, written in TypeScript)
get correct Ecopower cost figures without reimplementing the tariff formula
themselves. Mirrors compare_tariffs.py's config/wiring.
"""
import dataclasses
import os
from datetime import datetime
from typing import Literal

from fastapi import FastAPI, HTTPException

from ecopower_tarrifs.adapters.influxdb_repository import (
    InfluxDBPowerReadingRepository,
    InfluxDBEpexPriceRepository,
)
from ecopower_tarrifs.domain.models import MonthlyCostBreakdown
from ecopower_tarrifs.domain.tariff_calculator import EcopowerTariffCalculator
from ecopower_tarrifs.services.cost_calculation_service import MonthlyCostCalculationService
from ecopower_tarrifs.services.fixed_cost_calculation_service import (
    FixedMonthlyCostCalculationService,
)

app = FastAPI(title="ecopower-tariffs API")

INFLUXDB_HOST = os.getenv("INFLUXDB_HOST", "192.168.1.5")
INFLUXDB_PORT = int(os.getenv("INFLUXDB_PORT", "8086"))
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "victoor.io")
METERING_BUCKET = os.getenv("METERING_BUCKET", "metering")
PRICES_BUCKET = os.getenv("PRICES_BUCKET", "energy_prices")


def _breakdown_to_dict(b: MonthlyCostBreakdown) -> dict:
    d = dataclasses.asdict(b)
    d["total_cost"] = b.total_cost
    d["average_price_per_kwh_ex_vat"] = b.average_price_per_kwh_ex_vat
    d["average_price_per_kwh_incl_vat"] = b.average_price_per_kwh_incl_vat
    return d


def _make_dynamic_service() -> MonthlyCostCalculationService:
    return MonthlyCostCalculationService(
        power_repository=InfluxDBPowerReadingRepository(
            host=INFLUXDB_HOST, port=INFLUXDB_PORT, token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG, bucket=METERING_BUCKET,
        ),
        price_repository=InfluxDBEpexPriceRepository(
            host=INFLUXDB_HOST, port=INFLUXDB_PORT, token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG, bucket=PRICES_BUCKET,
        ),
    )


def _make_fixed_service() -> FixedMonthlyCostCalculationService:
    return FixedMonthlyCostCalculationService(
        power_repository=InfluxDBPowerReadingRepository(
            host=INFLUXDB_HOST, port=INFLUXDB_PORT, token=INFLUXDB_TOKEN,
            org=INFLUXDB_ORG, bucket=METERING_BUCKET,
        ),
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/price/per-kwh")
def price_per_kwh(epex_eur_mwh: float, direction: Literal["consumption", "injection"] = "consumption"):
    """Stateless lookup: the actual all-in €/kWh price for a given EPEX value.

    No InfluxDB access — callers who already have an EPEX price (e.g. for a
    specific EV charging session window) can get the correct formula applied
    without needing to know the underlying tariff constants themselves.
    """
    if direction == "consumption":
        price = EcopowerTariffCalculator.calculate_energy_cost_per_kwh(epex_eur_mwh)
        price += EcopowerTariffCalculator.DISTRIBUTION_TARIFF
        price += EcopowerTariffCalculator.GSC_TARIFF
        price += EcopowerTariffCalculator.WKK_TARIFF
        price += EcopowerTariffCalculator.ENERGY_CONTRIBUTION
        price += EcopowerTariffCalculator.EXCISE_TAX
    else:
        price = EcopowerTariffCalculator.calculate_energy_revenue_per_kwh(epex_eur_mwh)

    return {"epex_eur_mwh": epex_eur_mwh, "direction": direction, "price_eur_kwh": price}


@app.get("/cost")
def cost(year: int, month: int, tariff: Literal["dynamic", "fixed"] = "dynamic"):
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="month must be 1-12")

    service = _make_dynamic_service() if tariff == "dynamic" else _make_fixed_service()
    breakdown = service.calculate_monthly_cost(year, month)
    return _breakdown_to_dict(breakdown)


@app.get("/cost/current")
def cost_current(tariff: Literal["dynamic", "fixed"] = "dynamic"):
    now = datetime.now()
    return cost(year=now.year, month=now.month, tariff=tariff)


@app.get("/cost/range")
def cost_range(start: str, end: str):
    """Energy cost for an arbitrary [start, end) ISO-8601 range.

    Excludes fixed/data-management/capacity costs, which are only
    meaningful for a full calendar month — use /cost for those.
    """
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except ValueError:
        raise HTTPException(status_code=400, detail="start/end must be ISO-8601 timestamps")

    service = _make_dynamic_service()
    breakdown = service.calculate_range_cost(start_dt, end_dt)
    return _breakdown_to_dict(breakdown)


@app.get("/cost/comparison")
def cost_comparison(year: int, month: int):
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="month must be 1-12")

    dynamic_result = _make_dynamic_service().calculate_monthly_cost(year, month)
    fixed_result = _make_fixed_service().calculate_monthly_cost(year, month)

    difference = fixed_result.total_cost - dynamic_result.total_cost
    percentage = (
        (difference / dynamic_result.total_cost) * 100
        if dynamic_result.total_cost else 0.0
    )

    return {
        "dynamic": _breakdown_to_dict(dynamic_result),
        "fixed": _breakdown_to_dict(fixed_result),
        "cheaper_tariff": "dynamic" if difference > 0 else "fixed" if difference < 0 else "equal",
        "savings_eur": abs(difference),
        "savings_percent": percentage,
    }
