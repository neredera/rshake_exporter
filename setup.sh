#!/bin/bash

# go to current directory
cd "${0%/*}"

# install needed packages
#sudo apt-get update
sudo apt-get install git python3-venv python3-pip

# activate a virtual environment
#python3 -m venv .

# install python modules
python3 -m pip install prometheus_client PyParsing

# user for service
useradd -Mr rshake_exporter
usermod -L rshake_exporter
# usermod -aG root rshake_exporter
# usermod -aG sudo rshake_exporter

chmod +x exporter.py

# sudo systemctl daemon-reload

sudo systemctl enable $(pwd)/rshake_exporter.service

sudo systemctl start rshake_exporter.service

python3 exporter.py --help

sudo systemctl status rshake_exporter.service

#python3 exporter.py
