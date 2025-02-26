import os
import sys
import json
import csv
from collections import defaultdict
import argparse
import tldextract
import yaml

IP_LIST_FILE = '/home/hutr/iot-longitudinal/output_destination/{device_dataset}/{year}{exp}/ip_list/all_ips.json'
OUTPUT_CONTACTED_DOMAINS_DIR = '/home/hutr/iot-longitudinal/output_destination/{device_dataset}/{year}{exp}/domain_list'

IP_TO_DOMAIN_FILE = '/home/hutr/iot-longitudinal/domain_data_new/domain_info_{year}-{month}.csv'
EXP_TIMEFRAME_FILE = '/home/hutr/iot-longitudinal/inputs/{year_optional_month}-datasets_device_timeframes.json' # ['2019', '2021', '2022-aug', '2022-nov', '2023', '2024-summer']

def parse_args(config_file:str):
    with open(config_file) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    device_dataset = config['IP_CONFIGS']['device_dataset']
    exp_year = config['IP_CONFIGS']['exp_year']
    exp_year_optional_month = config['IP_CONFIGS']['exp_year_optional_month']
    experiments = config['IP_CONFIGS']['experiments']
    
    parser = argparse.ArgumentParser(description='Convert IP to domain with uncontrolled DNS / TLS data')
    parser.add_argument('--device_dataset', type=str, required=False, default=device_dataset, help='Device dataset')
    
    args = parser.parse_args()
    return args.device_dataset, exp_year, exp_year_optional_month, experiments

def extract_sld(domain):
    # no_fetch_extract = tldextract.TLDExtract(suffix_list_urls=("https://raw.github.com/mozilla/gecko-dev/master/netwerk/dns/effective_tld_names.dat"))
    # no_cache_extract = tldextract.TLDExtract(cache_dir=False)
    ext = tldextract.extract(domain)
    # ext = no_cache_extract(domain)
    # if ext.suffix is None:
    #     return None
    return f"{ext.domain}.{ext.suffix}"

def parse_exp_timeframe(exp_timeframe_file:str)->dict[str: list[str]]:
    """Extract the timeframe for each year of experiments

    Returns:
        dict: key: device, value: list of months that the device was under experiment
    """
    with open(exp_timeframe_file, 'r') as f:
        exp_timeframe = json.load(f)
    for device in exp_timeframe:
        cur_month = set()
        for time_string in exp_timeframe[device]:
            if '-' not in time_string:
                continue
            _, month, _ = time_string.split('-')
            cur_month.add(month)
        exp_timeframe[device] = list(cur_month)
    return exp_timeframe

def parse_ip_to_domain(ip_to_domain_file)->dict[str: dict[str: str]]:
    """Parse the IP to domain file extracted from the DNS / TLS data

    Returns:
        dict: key: device, value: dict: key: IP, value: domain
    """
    ip_to_domain = defaultdict(dict)
    with open(ip_to_domain_file, 'r') as f:
        duplidated_count = 0
        all_count = 0
        reader = csv.DictReader(f)
        for row in reader:
            domain = row['Domain'].lower()
            sld = extract_sld(domain)
            if row['IP'] in ip_to_domain[row['Device']] and ip_to_domain[row['Device']][row['IP']] != sld: #  and row['Protocol'] == 'TLS'
                # print(f"Duplicate IP: {sld}, {ip_to_domain[row['Device']][row['IP']]} for device: {row['Device']}")
                duplidated_count += 1
            ip_to_domain[row['Device']][row['IP']] = sld
            all_count += 1
        print(f"Total: {all_count}, Duplicated: {duplidated_count}")
    return ip_to_domain

def parse_ip_to_domain_dns_tls_seperate(ip_to_domain_file)->tuple[dict[str: dict[str: str]], dict[str: dict[str: str]]]:
    """Parse the IP to domain file extracted from the DNS / TLS data. Seperate the DNS and TLS data for comparison

    Returns:
        tuple: (TLS dict: key: device, value: dict: key: IP, value: domain, 
        DNS dict: key: device, value: dict: key: IP, value: domain)
    """
    ip_to_domain_tls = defaultdict(dict)
    ip_to_domain_dns = defaultdict(dict)
    with open(ip_to_domain_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            domain = row['Domain'].lower()
            sld = extract_sld(domain)
            if row['Protocol'] == 'TLS':
                if row['IP'] in ip_to_domain_tls[row['Device']] and ip_to_domain_tls[row['Device']][row['IP']] != sld:
                    print(f"Duplicate IP TLS: {sld}, {ip_to_domain_tls[row['Device']][row['IP']]} for device: {row['Device']}")
                ip_to_domain_tls[row['Device']][row['IP']] = sld
            elif row['Protocol'] == 'DNS':
                if row['IP'] in ip_to_domain_dns[row['Device']] and ip_to_domain_dns[row['Device']][row['IP']] != sld:
                    print(f"Duplicate IP DNS: {sld}, {ip_to_domain_dns[row['Device']][row['IP']]} for device: {row['Device']}")
                ip_to_domain_dns[row['Device']][row['IP']] = sld

    return ip_to_domain_tls, ip_to_domain_dns

def parse_ip_list_json(ip_file)->dict[str: list[str]]:
    """Parse the IP list from the json file

    Returns:
        dict: list of IPs for each device. key: device, value: list of IPs
    """
    with open(ip_file, 'r') as f:
        ip_list = json.load(f)
    return ip_list

def extract_month_candidates(device_timeframe:list[str])->list[str]:
    """Extract the month candidates for the device

    Returns:
        list: month candidates for the device
    """
    month_candidates = set()
    for timeframe in device_timeframe:
        
        month_candidates.add(timeframe)
        # 05 > 04
        prev_month = str(int(timeframe) - 1).zfill(2)
        month_candidates.add(prev_month)
    return list(month_candidates)

def main():
    device_dataset, exp_year, exp_year_optional_month, experiments = parse_args("config/config.yaml")
    untranslated_stats_all = {}
    for year in exp_year: # ['2019', '2021', '2022', '2023', '2024']
        # get the timeframe for each device for the current year
        print(f"Processing {year}....")
        exp_timeframe = defaultdict(list)
        for year_optional_month in exp_year_optional_month: # ['2019', '2021', '2022-aug', '2022-nov', '2023', '2024-summer']
            if year in year_optional_month:
                cur_exp_timeframe_file = EXP_TIMEFRAME_FILE.format(year_optional_month=year_optional_month)
                exp_timeframe.update(parse_exp_timeframe(cur_exp_timeframe_file))
        # save exp_timeframe to json file
        with open(f"/home/hutr/iot-longitudinal/inputs/{year}_exp_timeframe.json", 'w') as f:
            json.dump(exp_timeframe, f, indent=4)
        print(f"year: {year}, exp_timeframe: {exp_timeframe}")
        continue
        ip_to_domain = defaultdict(dict)
        months = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12'] if year != '2024' else ['01', '02', '03', '04', '05', '06', '07', '08']
        for month in months:
            ip_to_domain[month] = defaultdict(dict)
            cur_ip_to_domain_file = IP_TO_DOMAIN_FILE.format(year=year, month=month)
            tmp_ip_to_domain = parse_ip_to_domain(cur_ip_to_domain_file)
            # _, tmp_ip_to_domain = parse_ip_to_domain_dns_tls_seperate(cur_ip_to_domain_file)
            for dev in tmp_ip_to_domain:
                ip_to_domain[month][dev] = defaultdict(str)
                for ip in tmp_ip_to_domain[dev]:
                    if ip in ip_to_domain[month][dev]:
                        print(f"Duplicate IP Domain: {tmp_ip_to_domain[dev][ip]}, {ip_to_domain[month][dev][ip]}")
                    ip_to_domain[month][dev][ip] = tmp_ip_to_domain[dev][ip]
        
        
        for exp in experiments:
            # get the IP list per device for the current year-experiment
            cur_ip_list_file = IP_LIST_FILE.format(device_dataset=device_dataset, year=year, exp=exp)
            cur_ip_list = parse_ip_list_json(cur_ip_list_file)
            cur_domain_list = defaultdict(set)
            untranslated_stats = {}
            untranslated_ip_dict = {}
            for device in cur_ip_list:
                if len(cur_ip_list[device]) == 0:
                    continue
                translated_ip = 0
                untranslated_ip = 0
                cur_domain_list[device] = set()
                untranslated_ip_dict[device] = set()
                device_timeframe = exp_timeframe[device]
                month_candidates = extract_month_candidates(device_timeframe)
                # month_candidates = months
                # get the IP to domain mapping for the current year-experiment
                cur_ip_to_domain = {"8.8.8.8":'dns.google', "155.33.33.75": "neu.edu", "155.33.33.70": "neu.edu"}   # ip: domain
                for month in month_candidates:
                    cur_ip_to_domain.update(ip_to_domain[month][device])
                # print(f'{device}:', cur_ip_to_domain)
                for ip in cur_ip_list[device]:
                    if ip in cur_ip_to_domain:
                        cur_domain_list[device].add(cur_ip_to_domain[ip])
                        translated_ip += 1
                    else:
                        # print(ip)
                        untranslated_ip += 1
                        untranslated_ip_dict[device].add(ip)
                # print(f"Device: {device}, Untranslated IPs: {untranslated_ip}, Total IPs: {translated_ip + untranslated_ip}")
                # save 
                
                untranslated_stats[device] = [untranslated_ip / (translated_ip + untranslated_ip), untranslated_ip, translated_ip + untranslated_ip]
            # exit(1)
            save_untranslated_stats(untranslated_stats, os.path.dirname(cur_ip_list_file))
            save_contacted_domains(cur_domain_list, OUTPUT_CONTACTED_DOMAINS_DIR.format(device_dataset=device_dataset, year=year, exp=exp))
            save_untranslated_ip(untranslated_ip_dict, os.path.dirname(cur_ip_list_file))
            total_untranslated = 0 
            total_ip = 0
            for device in untranslated_stats:
                total_ip += untranslated_stats[device][2]
                total_untranslated += untranslated_stats[device][1]
            untranslated_stats_all[(year, exp)] = [total_untranslated, total_ip]
    
    # print the statistics by year
    total_stats = [0, 0, 0]
    for year in exp_year:
        cur_year_stats = {}
        cur_year_stats[year] = [0, 0, 0]
        for exp in experiments:
            cur_year_stats[year][1] += untranslated_stats_all[(year, exp)][0]
            cur_year_stats[year][2] += untranslated_stats_all[(year, exp)][1]
        cur_year_stats[year][0] = cur_year_stats[year][1] / cur_year_stats[year][2]
        total_stats[1] += cur_year_stats[year][1]
        total_stats[2] += cur_year_stats[year][2]
        print(f"Year: {year}, Percentage Untranslated: {cur_year_stats[year][0]}, Untranslated IPs: {cur_year_stats[year][1]}, Total IPs: {cur_year_stats[year][2]}")
    total_stats[0] = total_stats[1] / total_stats[2]
    print(f"Total, Percentage Untranslated: {total_stats[0]}, Untranslated IPs: {total_stats[1]}, Total IPs: {total_stats[2]}")
        
def save_untranslated_ip(untranslated_ip: dict, output_dir: str):
    """
    Save the untranslated IPs.

    Args:
        untranslated_ip (dict): key: device, value: set of untranslated IPs.
        output_dir (str): Directory to save the results.
    """
    os.makedirs(output_dir, exist_ok=True)
    # convert set to list
    untranslated_ip = {device: list(ips) for device, ips in untranslated_ip.items()}
    # save as json file
    with open(os.path.join(output_dir, "untranslated_ips.json"), 'w') as f:
        json.dump(untranslated_ip, f, indent=4)

def save_contacted_domains(contacted_domains: dict, output_dir: str):
    """
    Save the contacted domains.

    Args:
        contacted_domains (dict): key: device, value: set of contacted domains.
        output_dir (str): Directory to save the results.
    """
    os.makedirs(output_dir, exist_ok=True)
    # convert set to list
    contacted_domains = {device: list(domains) for device, domains in contacted_domains.items()}
    # save as json file
    with open(os.path.join(output_dir, "contacted_slds_with_all_dns.json"), 'w') as f:
        json.dump(contacted_domains, f, indent=4)

def save_untranslated_stats(results: dict[list], output_dir: str):
    """
    Save the untranslated IP statistics.

    Args:
        results (dict): Mapping of devices to percentages of untranslated IPs.
        output_dir (str): Directory to save the results.
    """
    os.makedirs(output_dir, exist_ok=True)
    # save as csv file
    with open(os.path.join(output_dir, "_untranslated_ip_stats_with_all_dns.csv"), 'w') as f:
        writer = csv.writer(f)
        writer.writerow(["Device", "Percentage Untranslated", "Untranslated IPs", "Total IPs"])
        total_ip = 0
        total_untranslated = 0
        for device, stats in results.items():
            writer.writerow([device] + stats)
            total_untranslated += stats[1]
            total_ip += stats[2]
        writer.writerow(["Total", (total_untranslated / total_ip) * 100, total_untranslated, total_ip])
        
        
if __name__ == '__main__':
    
    main()