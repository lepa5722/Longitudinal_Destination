## Getting Started

## Geolocation Scripts

## Description
The two scripts in this directory are used to find the geolocations of either IP addresses or domain names contacted
by devices in a dataset. A Geolocation database that matches the month and year of the dataset you want to analyze
is required to run these scripts.

## Libraries Used
-  pyshark version 0.5.3
-  geoip2 version 4.8.0
-  tshark version 4.2.2

## Using Geolocation Databases
It is important that the geolocation database used in the analysis is from the month and year of the data collected,
as the geolocations of IP addresses and domain names change frequently. These can be found in historical archives of
geolocation databases online.

## Usage
### geolocation_extraction.py
The `geolocation_extraction.py` script looks at a directory of devices' PCAP files and pulls IP addresses from them. 
Those IP addresses are then mapped to a geolocation using the given geolocation database. The script creates a text 
file where the geolocations for each IP address of each device in the dataset is printed 
```
python3 geolocation_extraction.py /path/to/dataset /path/to/geolocation/database /path/to/outoput
```
An example usage is:
```
pyton3 geolocation_extraction.py /net/data/iot-longitudinal/datasets/2023-datasets/idle-dataset /net/data/iot-longitudinal/databases/dbip-country-lite-2023-06.mmdb /net/data/iot-longitudinal/results
```
The script is used for the RQ1.5

### geolocation_domain_extract.py
The `geolocation_domain_extract.py` script looks at a directory of devices' text file with a list of domains found for 
each device. Those domains are then put through DNS lookup, and mapped to a geolocation with the geolocation database.
This script can **only** be used for the current datasets. The script created a text file where the geolocations for each
domain of each device in the dataset is printed.
```
python3 geolocation_domain_extract.py /path/to/dataset /path/to/geolocation/database /path/to/output
```
Example usage is:
```
pyton3 geolocation_domain_extraction.py /net/data/iot-longitudinal/datasets/2023-datasets/text_file /net/data/iot-longitudinal/databases/dbip-country-lite-2023-06.mmdb /net/data/iot-longitudinal/results
```
This script is used for RQ1.5
