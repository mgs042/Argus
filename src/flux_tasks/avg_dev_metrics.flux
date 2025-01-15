option task = {
    name: "Dev_Metrics_Task",
    every: 5m
  }

packet_count = from(bucket: "uplink_metrics_log")
    |> range(start: -5m)
    |> filter(fn: (r) => r._measurement == "uplink_metrics")
    |> filter(fn: (r) => r._field == "f_cnt")
    |> group(columns: ["device_id"])
    |> count()
    |> map(fn: (r) => ({r with _measurement: "avg_device_metrics", _time: now(), _field: "packet_rate", _value: float(v: r._value)}))

avg_snr = from(bucket: "uplink_metrics_log")
    |> range(start: -5m)
    |> filter(fn: (r) => r._measurement == "uplink_metrics")
    |> filter(fn: (r) => r._field == "snr")
    |> group(columns: ["device_id"])
    |> mean()
    |> map(fn: (r) => ({r with _measurement: "avg_device_metrics", _time: now(), _field: "avg_snr", _value: r._value}))

avg_rssi = from(bucket: "uplink_metrics_log")
    |> range(start: -5m)
    |> filter(fn: (r) => r._measurement == "uplink_metrics")
    |> filter(fn: (r) => r._field == "rssi")
    |> group(columns: ["device_id"])
    |> mean()
    |> map(fn: (r) => ({r with _measurement: "avg_device_metrics", _time: now(), _field: "avg_rssi", _value: r._value}))

union(tables: [packet_count, avg_snr, avg_rssi])
    |> to(bucket: "dev_metrics", org: "Argus")