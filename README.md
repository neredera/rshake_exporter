# rshake_exporter

This is a [Prometheus exporter](https://prometheus.io/docs/instrumenting/exporters/) for [Raspberry Shakes](https://raspberryshake.org/) seismographs.

It is tested with the default Raspberry Shake image (version 0.18).

## Usage

Clone the repository und install with:
```bash
cd ~
git clone https://github.com/neredera/rshake_exporter.git
cd rshake_exporter
.\setup.sh
```

Enable/disable the sensors you need via:
```bash
nano rshake_exporter.service

sudo systemctl daemon-reload
sudo systemctl restart rshake_exporter.service
sudo systemctl status rshake_exporter.service
```

Command line parameters:
```bash
> python3 exporter.py --help

usage: exporter.py [-h] [--port PORT] [--integration INTEGRATION]

optional arguments:
  -h, --help            show this help message and exit
  --port PORT           The port where to expose the exporter (default:9984)
  --integration INTEGRATION
                        Time interval in seconds for collected data. Should be
                        equal to the Prometheus scrape interval (default:15)
                        
```

## Prometheus metrics

Example how to add the exporter to the prometheus configuration (`prometheus.yml`):
```yml
  - job_name: rshake
    static_configs:
    - targets:
      - rs.local:9984
```

Some sample metrics:

```
# HELP rshake_total_raw_values_total Total samples received
# TYPE rshake_total_raw_values_total counter
rshake_total_raw_values_total{channel="SHZ"} 105899.0
# HELP rshake_max_value Max Raw value in the last integration period
# TYPE rshake_max_value gauge
rshake_max_value{channel="SHZ"} 1188.0 1627400663000
# HELP rshake_min_value Min Raw value in the last integration period
# TYPE rshake_min_value gauge
rshake_min_value{channel="SHZ"} 577.0 1627400663000
# HELP rshake_zero_offset Estimated offset of raw values from zero
# TYPE rshake_zero_offset gauge
rshake_zero_offset{channel="SHZ"} 910.4954659333074 1627400663000
```
