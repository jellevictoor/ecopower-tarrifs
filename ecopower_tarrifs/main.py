
def get_fixed_cost():
    # ecopower + fluvius subscription cost
    return 5 + 2

def get_15m_cost(epex_da):
    return 0.00102 * epex_da + 0.004

def get_15m_revenue(epex_da):
    return  0.00098 * epex_da - 0.015

def cost_gsc(kWh: float):
    return 0.011 * kWh

def cost_wkk(kWh: float):
    return 0.00392 * kWh

def cost_power_delivery(no_of_kWh: float):
    return no_of_kWh * 0.0704386

def cost_power_injected(no_of_kWh: float):
    return no_of_kWh * 0.0017510

def yearly_cost(epex_da, kWh_gsc, kWh_wkk):
    return 17.51

def peak_per_month(peak_in_kw: float):
    return (peak_in_kw * 56.93) / 12
class Influx_Energy_Provider:
    def __init__(self, host, port, token, org, bucket):
        from influxdb_client import InfluxDBClient
        self.client = InfluxDBClient(url=f"http://{host}:{port}", token=token)
        self.org = org
        self.bucket = bucket
        self.query_api = self.client.query_api()
        self.write_api = self.client.write_api()

    def query(self, query):
        return self.query_api.query(org=self.org, query=query)

    def write(self, point):
        self.write_api.write(bucket=self.bucket, org=self.org, record=point)
class Influx_Energy_Price_Provider:
    def __init__(self, host, port, token, org, bucket):
        from influxdb_client import InfluxDBClient
        self.client = InfluxDBClient(url=f"http://{host}:{port}", token=token)
        self.org = org
        self.bucket = bucket
        self.query_api = self.client.query_api()
        self.write_api = self.client.write_api()

    def query(self, query):
        query = """from(bucket: "energy_prices")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r["_measurement"] == "electricity_price")
  |> filter(fn: (r) => r["_field"] == "price_eur_kwh")
  |> aggregateWindow(every: v.windowPeriod, fn: mean, createEmpty: false)
  |> yield(name: "mean")"""
        return self.query_api.query(org=self.org, query=query)

    def write(self, point):
        self.write_api.write(bucket=self.bucket, org=self.org, record=point)
def __main__():
    Influx_Energy_Provider(host='192.168.1.5', port=8086, token='', org='victoor.io', bucket='energy_data')
    Influx_Energy_Price_Provider(host='192.