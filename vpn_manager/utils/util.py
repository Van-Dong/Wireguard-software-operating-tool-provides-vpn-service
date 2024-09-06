from vpn_manager.config import *
from vpn_manager import global_variables as g
from datetime import datetime
import os, time, requests, socket
from ipaddress import ip_address, IPv4Interface, IPv6Interface, ip_network

from vpn_manager.models.interface import Interface
from vpn_manager.models.globalsetting import GlobalSetting
from vpn_manager.models.vpnconnection import VpnConnection
from django.forms.models import model_to_dict
import subprocess

import logging
# Tạo logger
logger = logging.getLogger(__name__)


# # Need handler exception when no internet not connected
def get_ip_public():
    url = "https://api.ipify.org?format=json"

    ip = 'N/A'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            ip = data["ip"]
        else:
            ip = "N/A"
    except Exception:
        ip = "N/A" 
    return ip

def get_ip_local():  # ip of computer 
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    ip = 'N/A'
    try:
        # doesn't even have to be reachable
        s.connect(("10.254.254.254", 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = "N/A"
    finally:
        s.close()
    return ip

def get_cur_ip():
    if DEFAULT_ENDPOINT_ADDRESS == "local":
        return get_ip_local()
    else:
        return get_ip_public()

# return [public_ip, private_ip]
def get_list_ip():
    public_ip = get_ip_public()
    local_ip = get_ip_local()
    return [public_ip, local_ip]

# 192.168.2.1
def is_valid_ip(ip):
    try:
        ip_address(ip)
        return True
    except ValueError:
        return False

# 192.168.1.2/24
def is_valid_ipv4_interface(address):  
    try:
        IPv4Interface(address)  # accept both ip network and ip host
        return True
    except ValueError:
        return False
def is_valid_ipv6_interface(address):
    try:
        IPv6Interface(address)
        return True
    except ValueError:
        return False

def check_is_overlap_network(ip_check, list_ip):
    try:
        networks = [ip_network(ip, strict=False) for ip in list_ip]
        network_check = ip_network(ip_check, strict=False)
    except Exception as e:
        print(e)
    for x in networks:
        if network_check.overlaps(x):
            return True, str(x)
    
    return False, ''

def get_interface(id):
    try:
        interface = Interface.objects.get(pk=id)
        interface = model_to_dict(interface)
        interface['addresses'] = interface['addresses'].split(', ')
        return interface    
    except Exception as e:
        return False

def get_global_setting():
    try:
        global_setting = GlobalSetting.objects.last()
        global_setting = model_to_dict(global_setting)
        global_setting['dns_servers'] = global_setting['dns_servers'].split(', ')
        return global_setting
    except Exception as e:
        return False

def get_peer(id):
    
    try:
        peer = VpnConnection.objects.get(pk=id)
        # Chuyển đối tượng Peer sang dictionary
        peer_dict = model_to_dict(peer)
        
        # convert string to list
        peer_dict['allocated_ips'] = peer_dict['allocated_ips'].split(', ')
        peer_dict['allowed_ips'] = peer_dict['allowed_ips'].split(', ')
        if peer_dict['extra_allowed_ips'] != '':
            peer_dict['extra_allowed_ips'] = peer_dict['extra_allowed_ips'].split(', ')
        else:
            peer_dict['extra_allowed_ips'] = []
        return peer_dict
    except Exception as e:
        return False

def get_peers_in_interface(interface_id):
    try:
        peers = list(VpnConnection.objects.filter(interface_id=interface_id).values())  # không ép kiểu sang list cũng được (dạng QuerySet vẫn lặp bằng for/in như thường)
        return peers # các field có nhiều giá trị đang ở dạng xâu 
    except Exception as e:
        return False

# for g.curr_client_run
def get_info_client(clients):
    result = {}
    for client in clients:
        result[client['public_key']] = {
            'id': client['id'],
            'name': client['name'],
            'email': client['email'],
            'additional_notes': client['additional_notes']
        }
    return result

def get_name_interface_wireguard():
    global_setting = get_global_setting()
    return global_setting['name_interface']

def create_client_config(id):
    client = get_peer(id)

    if client == False: return False
    if client['interface'] == None:
        return False
    
    interface = get_interface(client['interface'])
    
    if interface == False:
        return False
    # handle client
    preshared_key = ''
    if client['preshared_key'] != "":
        preshared_key = f"PresharedKey = {client['preshared_key']}"
    
    # handle global_setting
    global_setting = get_global_setting()
    dns = ''
    persistent_keep_alive = ''
    mtu = ''
    endpoint = ''
    if global_setting != False:
        global_setting['dns_servers'] = ', '.join(global_setting['dns_servers'])
        if global_setting['dns_servers'] != '':
            dns = f'DNS = {global_setting["dns_servers"]}'
        if global_setting['persistent_keepalive'] != 0:
            persistent_keep_alive = f'PersistentKeepalive = {global_setting["persistent_keepalive"]}'
        if global_setting['mtu'] is not None:
            mtu = f'MTU = {global_setting["mtu"]}'
        endpoint = f'Endpoint = {global_setting["endpoint_address"]}:{interface["listen_port"]}'
    else:
        ip_endpoint = get_cur_ip()
        if ip_endpoint != "N/A":
            endpoint = f'Endpoint = {ip_endpoint}:{interface["listen_port"]}'
        

    # create content of client.conf
    client_config = f"""[Interface]
Address = {', '.join(client['allocated_ips'])}
PrivateKey = {client['private_key']}
{dns}
{mtu}

[Peer]
PublicKey = {interface['public_key']}
{preshared_key}
AllowedIPs = {', '.join(client['allowed_ips'])}
{persistent_keep_alive}
{endpoint}
"""
    return [client_config, client['name']]


def write_server_config(interface_id):
    # server_config = get_server() # server = interface + global_settings
    interface = get_interface(interface_id)
    global_setting = get_global_setting()  
    peers = get_peers_in_interface(interface_id)  # chú ý: ở đây các trường mà có nhiều địa chỉ ip thì nó ở dạng xâu 
    now = datetime.now().isoformat()
    
    if interface == False or peers == False or global_setting == False:
        return False

    mtu = ''
    persistent_keepalive = ''
    if global_setting['mtu'] is not None: mtu = f'MTU = {global_setting["mtu"]}'
    if global_setting['persistent_keepalive'] == 0: persistent_keepalive = ''
    else: persistent_keepalive = f'PersistentKeepalive = {global_setting["persistent_keepalive"]}'

    # create peer content for file server config
    peer_content = ""
    for peer in peers:
        if peer['enabled'] == True:
            if peer['preshared_key'] != "": 
                peer['preshared_key'] = "PresharedKey = " + peer['preshared_key']
    
            allowed_ips = peer['allocated_ips']
            if peer['extra_allowed_ips'] != '':
                allowed_ips = allowed_ips + ', ' + peer['extra_allowed_ips']

            if peer['endpoint'] != "":
                peer['endpoint'] = "Endpoint = " + peer['endpoint']
        
            peer_content += f"""
# Name:       {peer['name']}
# Email:      {peer['email']}
# Created at: {peer['created_at']}
# Updated at: {peer['updated_at']}
[Peer]
PublicKey = {peer['public_key']}
AllowedIPs = {allowed_ips}
{peer['preshared_key']}
{persistent_keepalive}
{peer['endpoint']}
"""

    # create interface of file server config
    content = f"""# Created at: {now}
[Interface]
Address = {', '.join(interface['addresses'])}
ListenPort = {interface['listen_port']}
PrivateKey = {interface['private_key']}
PreUp = {interface['pre_up']}
PostUp = {interface['post_up']}
PreDown = {interface['pre_down']}
PostDown = {interface['post_down']}
Table = {global_setting['table']}
{mtu}
    """

    content += peer_content # append list [peer] to [interface]

    # Create file *.conf
    tmp_file = CONFIG_JSON_FOLDER_PATH + 'tmp.conf'
    config_file = f"/etc/wireguard/{interface['name']}.conf"
    try:
        with open(tmp_file, 'w') as f:
            f.write(content)
    except:
        return False
    
    # move file config to /etc/wireguard/
    sudo_password = os.getenv('PASSWORD')
    command_mv_file = f"mv {tmp_file} {config_file}"
    command_mv_file = command_mv_file.split()
    cmd1 = subprocess.Popen(['echo',sudo_password], stdout=subprocess.PIPE)
    cmd2 = subprocess.Popen(['sudo','-S'] + command_mv_file, stdin=cmd1.stdout, stdout=subprocess.PIPE)
    cmd2.wait()
    if cmd2.returncode == 0: 
        return interface['name']
    else:
        return False


def handle_error_apply_conf(error):
    # [#] 
    # [#] ip link add wg1 type wireguard
    # [#] wg setconf wg1 /dev/fd/63
    # Warning: AllowedIP has nonzero host part: 10.252.1.3/24
    # [#] ip -4 address add 10.252.1.1/32 dev wg1
    # [#] ip link set mtu 1420 up dev wg1
    # [#] ip -4 route add 10.252.1.9/32 dev wg1
    # [#] ip -4 route add 10.252.1.1/32 dev wg1
    # [#] ip -4 route add 10.252.1.0/24 dev wg1
    # RTNETLINK answers: File exists
    # [#] ip link delete dev wg1
    lines = error.split('\n')
    result = [line.strip() for line in lines if not line.strip().startswith('[#]')]
    return '\n'.join(result)

# bật wireguard interface thôi (đầu vào là interface_id or interface_name)
def enable_interface(interface_id):
    interface = ''
    try:
        interface = write_server_config(interface_id)
    except Exception as e:
        print(str(e))
    if interface == False:
        return {'status': False, 'message': 'Create File Server Config Failed'}
        
    # # Stop wg interface trùng với wg interface chuẩn bị bật
    if interface in list_wg_interfaces_running():
        stop_interface(interface)
        g.is_run = False
    
    # # Đánh dấu phiên mới trong wireguard server 
    # peerStatusEmpty = VpnConnectionStatus(type=2)
    # peerStatusEmpty.save()
    
    # Start wg interface
    sudo_password = os.getenv('PASSWORD')
    command_up_interface = f"wg-quick up {interface}"
    command_up_interface = command_up_interface.split()
    cmd1 = subprocess.Popen(['echo',sudo_password], stdout=subprocess.PIPE)
    cmd2 = subprocess.Popen(['sudo', '-S'] + command_up_interface, stdin=cmd1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cmd2.wait()
    stdout, stderr = cmd2.communicate()
    if cmd2.returncode == 0:
        g.is_run = True 
        
        return {'status': True, 'message': 'Apply config successfuly!'}
    else:
        errors = handle_error_apply_conf(stderr.decode('utf-8'))  # error khong co [#] o phia truoc, <class 'bytes'>
        return {"status": False, 'message': errors}

# for only client config change, server config not change
def sync_conf(interface_name, interface_id):
    
    # check wg interface is running ?
    if interface_name not in list_wg_interfaces_running():
        return {'status': True, 'message': f'Wg {interface_name} is not running!'} 
    
    interface = ''
    try:
        interface = write_server_config(interface_id)
    except Exception as e:
        return {'status': False, 'message': f'Error: {str(e)}'} 
    
    if interface == False:
        return {'status': False, 'message': 'Create File Server Config Failed'} 
    
    # run command stop wg interface
    sudo_password = os.getenv('PASSWORD')
    # command_up_interface = f"wg syncconf {interface} <(wg-quick strip {interface})"
    
    cmd_echo_password = subprocess.Popen(['echo',sudo_password], stdout=subprocess.PIPE)
    strip_command = f"wg-quick strip {interface}"
    strip_command = strip_command.split()
    strip_process = subprocess.Popen(['sudo', '-S'] + strip_command, stdin=cmd_echo_password.stdout, stdout=subprocess.PIPE)
    cmd_echo_password.stdout.close()
    strip_process.wait()
    strip_stdout, strip_stderr = strip_process.communicate()
    sync_content = strip_stdout.decode('utf-8') 
    
    temp_file_path = BACKUP_FOLDER_PATH + f'temp/{interface}.conf'
    with open(temp_file_path, 'w', encoding='utf-8') as file:
        file.write(sync_content)
    
    cmd_echo_password = subprocess.Popen(['echo',sudo_password], stdout=subprocess.PIPE)
    sync_command = f"wg syncconf {interface} {temp_file_path}"
    sync_command = sync_command.split()
    sync_process = subprocess.Popen(['sudo', '-S'] + sync_command, stdin=cmd_echo_password.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    cmd_echo_password.stdout.close()
    sync_process.wait()
    stdout, stderr = sync_process.communicate()
    
    
    if sync_process.returncode == 0:
        g.is_run = False
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        return {'status': True, 'message': 'Wireguard server synchronization successful!'}
    else:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        return {'status': False, 'message': stderr.decode('utf-8')}


def stop_interface(interface):
    
    # check wg interface is running ?
    if interface not in list_wg_interfaces_running():
        return {'status': True, 'message': f'Wg {interface} is not running!'} 
    
    # run command stop wg interface
    sudo_password = os.getenv('PASSWORD')
    command_up_interface = f"wg-quick down {interface}"
    command_up_interface = command_up_interface.split()
    cmd1 = subprocess.Popen(['echo',sudo_password], stdout=subprocess.PIPE)
    cmd2 = subprocess.Popen(['sudo', '-S'] + command_up_interface, stdin=cmd1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cmd2.wait()
    stdout, stderr = cmd2.communicate()
    
    if cmd2.returncode == 0:
        g.is_run = False
        return {'status': True, 'message': 'Stop wireguard interface successfuly!'}
    else:
        # print(stderr) # b"wg-quick: `wg1' is not a WireGuard interface\n" <class 'bytes'>
        # stderr.decode('utf-8')  # string 
        return {'status': False, 'message': stderr.decode('utf-8')}

# check server is run, don't need sudo
def check_server_is_run():
    # if server run --> wg show return: "Unable to access interface server: Operation not permitted"
    # else --> wg show return: ""
    command_check = "wg show" 
    command_check = command_check.split()
    
    cmd = subprocess.Popen(command_check, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cmd.wait()
    
    if cmd.returncode == 0:  # success --> return ""
        return False
    else:
        return True

def list_wg_interfaces_running(): # don't need sudo
    command_check = "wg show interfaces" 
    command_check = command_check.split()

    cmd = subprocess.Popen(command_check, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cmd.wait()
    stdout, stderr = cmd.communicate()
    
    if cmd.returncode == 0:  # success --> return ""
        return stdout.decode('utf-8').split()  # VD: ['server', 'wg1']
    else:
        return []

