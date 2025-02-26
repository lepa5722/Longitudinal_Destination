import socket
import geoip2.database
import os
import sys

# Devices to exclude
EXCLUDED_DEVICES = {'smartlife-bulb2', 'echoflex1', 'echoshow8', 
                    'ring-doorbell-wired', 'meross-plug2', 'ikettle', 'echoplus'}

# Function to resolve a domain to its IP address
def resolve_domain_to_ip(domain):
    try:
        return socket.gethostbyname(domain)
    except socket.gaierror:
        return None

# Function to process a device's domain list and return geolocation data
def process_device_domains(device_name, device_path, reader_country):
    domain_files = [f for f in os.listdir(device_path) if f.endswith('.txt')]
    results = []

    for domain_file in domain_files:
        file_path = os.path.join(device_path, domain_file)
        with open(file_path, 'r') as f:
            domains = [line.strip() for line in f if line.strip()]

        for domain in domains:
            ip = resolve_domain_to_ip(domain)
            if ip:
                try:
                    country_info = reader_country.country(ip)
                    result = f"Domain: {domain}, IP: {ip}, Country: {country_info.country.name}"
                except geoip2.errors.AddressNotFoundError:
                    result = f"Domain: {domain}, IP: {ip} - Location not found in database"
            else:
                result = f"Domain: {domain} - Could not resolve to IP"
            
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
        device_results = process_device_domains(device, device_path, reader_country)
        
        # Save results to a text file in the output directory
        output_file = os.path.join(output_dir, f"{device}_domain_geolocation.txt")
        with open(output_file, 'w') as f:
            f.write(f"Device: {device}\n" + "\n".join(device_results))
        print(f"Results saved for device {device} in {output_file}")
    
    reader_country.close()

# Main function
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python3 script.py <input dataset> <geolocation file> <output directory>")
        sys.exit(1)

    dataset_path = sys.argv[1]
    country_db_path = sys.argv[2]
    output_dir = sys.argv[3]

    process_dataset(dataset_path, country_db_path, output_dir)
