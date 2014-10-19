#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import requests
import time

size_id = 66         # 512MB RAM
region_id = 9        # AMS 3
image_id = 6372526   # Debian 7.0 x64

if len(sys.argv) == 1:
    print('Usage: deploy.py --client-id <my_client_id> --api-key <my_api_key> --domain <mydomain.nohost.me> [--password <my_password>] [--ssh-key-name <ssh_key>] [--no-snapshot] [--update-snapshot] [--test] [--system-upgrade]')
    sys.exit(1)

api_url = 'https://api.digitalocean.com/v1'
test = '--test' in sys.argv
snapshot = '--no-snapshot' not in sys.argv
update_snapshot = '--update-snapshot' in sys.argv
system_upgrade = '--system-upgrade' in sys.argv
postinstall = False

if '--domain' not in sys.argv:
    print('You have to provide a domain name')
    sys.exit(1)
if '--client-id' not in sys.argv:
    print('You have to provide a client ID')
    sys.exit(1)
if '--api-key' not in sys.argv:
    print('You have to provide an API key')
    sys.exit(1)

for key, arg in enumerate(sys.argv):
    if arg == '--domain':
        domain = sys.argv[key+1]
    if arg == '--password':
        postinstall = True
        password = sys.argv[key+1]
    if arg == '--api-key':
        api_key = sys.argv[key+1]
    if arg == '--client-id':
        client_id = sys.argv[key+1]
    if arg == '--ssh-key-name':
        ssh_key_name = sys.argv[key+1]

credentials = { 'client_id': client_id, 'api_key': api_key }

start = time.time()

# Check if YunoHost snapshot exists
if snapshot or update_snapshot:
    params = credentials
    params['filter'] = 'my_images'
    print('Getting snapshots...')
    r = requests.get(api_url +'/images', params=params)
    result = r.json()
    for image in result['images']:
        if image['name'] == 'YunoHost':
            print('Snapshot found: YunoHost')
            if update_snapshot:
                r = requests.get(api_url +'/images/'+ str(image['id']) + '/destroy', params=params)
                result = r.json()
                if result['status'] == 'ERROR':
                    print('Failed to remove "YunoHost" snapshot')
                    sys.exit(1)
                else:
                    print('Snapshot removed: YunoHost')
            else:
                image_id = image['id']

params = credentials

# Check if SSH key auth
if ssh_key_name:
    print('Getting SSH keys...')
    r = requests.get(api_url +'/ssh_keys', params=params)
    result = r.json()
    if len(result['ssh_keys']) > 0:
        for key in result['ssh_keys']:
            if key['name'] == ssh_key_name:
                params['ssh_key_ids'] = key['id']
        if params['ssh_key_ids'] is None:
            print('SSH key not found: '+ ssh_key_name)
            sys.exit(1)
    else:
        print('No SSH key found')
        sys.exit(1)

params.update({
    'name': domain,
    'image_id': image_id,   # Debian 7.0 x64 by default
    'size_id': size_id,     # 512MB by default
    'region_id': region_id  # AMS3 by default
})

sys.stdout.write('Creating your droplet, it may take a while...')
sys.stdout.flush()
r = requests.get(api_url +'/droplets/new', params=params)
result = r.json()
if result['status'] == 'ERROR':
    print('Failed to create droplet: '+ result['error_message'])
    sys.exit(1)

droplet = str(result['droplet']['id'])

# Display a dot every 10 seconds
while True:
    time.sleep(10)
    sys.stdout.write('.')
    sys.stdout.flush()
    params = credentials
    r = requests.get(api_url +'/droplets/'+ droplet, params=params)
    result = r.json()
    if result['droplet']['status'] == 'active':
        ip = result['droplet']['ip_address']
        time.sleep(20)
        break

print(' Droplet IP: '+ ip)
os.system('ssh-keygen -R '+ ip)

if image_id == 6372526:
    command_list = [
            'echo "root:M3ryOPF.AfR2E" | chpasswd -e', # Change root password to "yunohost"
            'git clone http://github.com/YunoHost/install_script /root/install_script'
    ]
    if system_upgrade:
        command_list.append('apt-get update && apt-get upgrade -qq -y')
    if test:
        command_list.append('cd /root/install_script && ./autoinstall_yunohostv2 test')
    else:
        command_list.append('cd /root/install_script && ./autoinstall_yunohostv2')

    print('Installing YunoHost on your droplet, it WILL take a while')
    for command in command_list:
        command_result = os.system('ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no "root@'+ ip +'" "export TERM=linux; '+ command +'"')
        if command_result != 0:
            print('Error during install command: '+ command)
            print('Result: '+ str(command_result))
            #sys.exit(1)

if snapshot and image_id == 6372526:
    sys.stdout.write('Shutting your droplet down, it may take a while...')
    sys.stdout.flush()
    requests.get(api_url +'/droplets/'+ droplet +'/power_off', params=credentials)
    while True:
        time.sleep(10)
        sys.stdout.write('.')
        sys.stdout.flush()
        r = requests.get(api_url +'/droplets/'+ droplet, params=credentials)
        result = r.json()
        if result['droplet']['status'] == 'off':
            break

    print(' Droplet off')
    params = credentials
    params['name'] = 'YunoHost'
    sys.stdout.write('Snapshooting your droplet, it may take a while...')
    sys.stdout.flush()
    requests.get(api_url +'/droplets/'+ droplet +'/snapshot', params=params)
    while True:
        time.sleep(10)
        sys.stdout.write('.')
        sys.stdout.flush()
        r = requests.get(api_url +'/droplets/'+ droplet, params=credentials)
        result = r.json()
        if result['droplet']['status'] == 'active':
            time.sleep(20)
            break

    print(' Snapshot created: YunoHost')

postinst_command_list = []

if postinstall:
    postinst_command_list.append('yunohost tools postinstall --domain '+ domain +' --password '+ password)

for command in postinst_command_list:
    command_result = os.system('ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no "root@'+ ip +'" "export TERM=linux; '+ command +'"')
    if command_result != 0:
        print('Error during postinst command: ' + command)


print('')
print('Successfully installed in '+ str(time.time() - start) +' s')
print('')
print('Connect to your droplet with "ssh root@'+ ip +'"')
sys.exit(0)

