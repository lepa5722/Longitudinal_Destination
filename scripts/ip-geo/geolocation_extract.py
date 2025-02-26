import pyshark
import geoip2.database
import os
import sys

# Devices to exclude: list the names of any devices that should be excluded from analysis
# ex: if you don't want to look at 'smartlife-bulb' add 'smartlife-bulb to EXCLUDED_DEVICES
EXCLUDED_DEVICES = {}

# Function to extract IP addresses from a PCAP file
def extract_ip_addresses_from_pcap(pcap_file):
    ip_addresses = set()
    cap = pyshark.FileCapture(pcap_file, display_filter="ip.dst", keep_packets=False)
    for packet in cap:
        try:
            ip_addresses.add(packet.ip.dst)
        except AttributeError:
            continue
    cap.close()
    return ip_addresses

# Function to process a device's PCAP files and return geolocation data
def process_device(device_name, device_path, reader_country):
    ip_addresses = set()

    # Go through each PCAP file directly in the device's directory
    for file in os.listdir(device_path):
        if file.endswith('.pcap'):
            pcap_file = os.path.join(device_path, file)
            print(f"Processing PCAP file: {pcap_file}")
            ip_addresses.update(extract_ip_addresses_from_pcap(pcap_file))

    results = []
    for ip in ip_addresses:
        try:
            country_info = reader_country.country(ip)
            result = f"IP: {ip}, Country: {country_info.country.name}"
        except geoip2.errors.AddressNotFoundError:
            result = f"IP: {ip} - Location not found in database"
        
        results.append(result)
    
    return results

# Function to process the dataset
def process_dataset(dataset_path, country_db_path, output_dir):
    reader_country = geoip2.database.Reader(country_db_path)

    devices = filter(lambda d: os.path.isdir(os.path.join(dataset_path, d)) and d not in EXCLUDED_DEVICES, os.listdir(dataset_path))
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for device in devices:
        device_path = os.path.join(dataset_path, device)
        device_results = process_device(device, device_path, reader_country)
        
        # Save results to a text file in the output directory
        output_file = os.path.join(output_dir, f"{device}_geolocation.txt")
        with open(output_file, 'w') as f:
            f.write(f"Device: {device}\n" + "\n".join(device_results))
        print(f"Results saved for device {device} in {output_file}")
    
    reader_country.close()

# Main function
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python3 script.py <input dataset> <geolocation database> <output directory>")
        sys.exit(1)

    dataset_path = sys.argv[1]
    country_db_path = sys.argv[2]
    output_dir = sys.argv[3]

    process_dataset(dataset_path, country_db_path, output_dir)
