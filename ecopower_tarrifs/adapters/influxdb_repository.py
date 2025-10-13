"""InfluxDB adapter implementations"""
from datetime import datetime
from typing import List

from influxdb_client import InfluxDBClient

from ..domain.models import PowerReading, EpexPrice
from ..domain.timestamp_utils import floor_to_15_minutes
from ..ports.repositories import PowerReadingRepository, EpexPriceRepository


class InfluxDBPowerReadingRepository(PowerReadingRepository):
    """InfluxDB implementation for power reading repository"""

    def __init__(self, host: str, port: int, token: str, org: str, bucket: str = "metering"):
        """
        Initialize InfluxDB connection for power readings

        Args:
            host: InfluxDB host
            port: InfluxDB port
            token: Authentication token
            org: Organization name
            bucket: Bucket name (default: "metering")
        """
        self.client = InfluxDBClient(url=f"http://{host}:{port}", token=token)
        self.org = org
        self.bucket = bucket
        self.query_api = self.client.query_api()

    def get_consumption_readings(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[PowerReading]:
        """Fetch power consumption readings from InfluxDB"""
        start_str = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_str = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')

        query = f'''
from(bucket: "{self.bucket}")
  |> range(start: {start_str}, stop: {end_str})
  |> filter(fn: (r) => r["_measurement"] == "energy")
  |> filter(fn: (r) => r["device"] == "p1meter")
  |> filter(fn: (r) => r["_field"] == "PowerDelivered")
  |> aggregateWindow(every: 15m, fn: mean, createEmpty: false)
'''

        result = self.query_api.query(org=self.org, query=query)

        readings = []
        for table in result:
            for record in table.records:
                # Normalize timestamp to 15-minute boundary
                timestamp = floor_to_15_minutes(record.get_time())
                readings.append(
                    PowerReading(
                        timestamp=timestamp,
                        power_kw=record.get_value()
                    )
                )

        return readings

    def get_injection_readings(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[PowerReading]:
        """Fetch power injection readings from InfluxDB"""
        start_str = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_str = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')

        query = f'''
from(bucket: "{self.bucket}")
  |> range(start: {start_str}, stop: {end_str})
  |> filter(fn: (r) => r["_measurement"] == "energy")
  |> filter(fn: (r) => r["device"] == "p1meter")
  |> filter(fn: (r) => r["_field"] == "PowerReturned")
  |> aggregateWindow(every: 15m, fn: mean, createEmpty: false)
'''

        result = self.query_api.query(org=self.org, query=query)

        readings = []
        for table in result:
            for record in table.records:
                # Normalize timestamp to 15-minute boundary
                timestamp = floor_to_15_minutes(record.get_time())
                readings.append(
                    PowerReading(
                        timestamp=timestamp,
                        power_kw=record.get_value()
                    )
                )

        return readings

    def close(self):
        """Close the InfluxDB connection"""
        self.client.close()


class InfluxDBEpexPriceRepository(EpexPriceRepository):
    """InfluxDB implementation for EPEX price repository"""

    def __init__(self, host: str, port: int, token: str, org: str, bucket: str = "energy_prices"):
        """
        Initialize InfluxDB connection for EPEX prices

        Args:
            host: InfluxDB host
            port: InfluxDB port
            token: Authentication token
            org: Organization name
            bucket: Bucket name (default: "energy_prices")
        """
        self.client = InfluxDBClient(url=f"http://{host}:{port}", token=token)
        self.org = org
        self.bucket = bucket
        self.query_api = self.client.query_api()

    def get_prices(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[EpexPrice]:
        """Fetch EPEX day-ahead prices from InfluxDB"""
        start_str = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_str = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')

        query = f'''
from(bucket: "{self.bucket}")
  |> range(start: {start_str}, stop: {end_str})
  |> filter(fn: (r) => r["_measurement"] == "electricity_price")
  |> filter(fn: (r) => r["_field"] == "price_eur_mwh")
  |> aggregateWindow(every: 15m, fn: mean, createEmpty: false)
'''

        result = self.query_api.query(org=self.org, query=query)

        prices = []
        for table in result:
            for record in table.records:
                # Normalize timestamp to 15-minute boundary
                timestamp = floor_to_15_minutes(record.get_time())
                prices.append(
                    EpexPrice(
                        timestamp=timestamp,
                        price_eur_mwh=record.get_value()
                    )
                )

        return prices

    def close(self):
        """Close the InfluxDB connection"""
        self.client.close()
