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
