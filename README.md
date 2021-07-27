# rshake_exporter

This is a [Prometheus exporter](https://prometheus.io/docs/instrumenting/exporters/) for [Raspberry Shakes](https://raspberryshake.org/) seismographs.

It is tested with the default Raspberry Shake image (version 0.18).

## Usage

Clone the respoitory und install with:
```bash
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
# HELP sensor_bmp085_temperature Temperature of pressure sensor bmp085/bmp180 in °C
# TYPE sensor_bmp085_temperature gauge
sensor_bmp085_temperature 15.4
# HELP sensor_bmp085_pressure Pressure of pressure sensor bmp085/bmp180 in hPa
# TYPE sensor_bmp085_pressure gauge
sensor_bmp085_pressure 997.08
```
