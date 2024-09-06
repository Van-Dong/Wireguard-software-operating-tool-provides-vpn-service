import subprocess, os, time, threading
from vpn_manager import global_variables as g

# lấy dữ liệu string trả về từ lệnh wg dump 
def fetch_data():
    sudo_password = os.getenv('PASSWORD')
    command = f"wg show all dump".split()
    cmd1 = subprocess.Popen(['echo',sudo_password], stdout=subprocess.PIPE)
    cmd2 = subprocess.Popen(['sudo', '-S'] + command, stdin=cmd1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cmd2.wait()
    stdout, stderr = cmd2.communicate()
    if cmd2.returncode == 0:
        # success: nếu không có wg interface nào chạy thì trả về  ""
        wg_dump = stdout.decode('utf-8')
        if wg_dump == "":
            g.is_run = False
        return wg_dump
    else:
        return False

# lấy dữ liệu client từ string của wg dump 
def convert_to_client_status(wg_dump):
    lines = wg_dump.strip().split('\n')
    parsed_data = []
    
    # Process each line
    curr_interface = ''
    for line in lines:
        fields = line.split('\t')
        if fields[0] == curr_interface:
            entry = {
                # "interface": fields[0],
        	    "public_key": fields[1], 
        	    "curr_endpoint": fields[3],   # (none) nếu không có 
        	    "latest_handshake": int(fields[5]) if len(fields) > 5 else None, # number int khoang 1.7 tỷ, 2033 là 2tỷ 
        	    "receive": int(fields[6]) if len(fields) > 6 else None,  # number 
        	    "transmit": int(fields[7]) if len(fields) > 7 else None,  # number
            }
            parsed_data.append(entry)
        else:
            curr_interface = fields[0]
            
    return parsed_data

def update_list_client_enabled():
    from vpn_manager.models.vpnconnection import VpnConnection
    objects = VpnConnection.objects.filter(enabled=True).values('public_key', 'id', 'name', 'email')
    g.curr_client_enabled = {}
    for obj in objects:
        g.curr_client_enabled[obj['public_key']] = {
            'id': obj['id'],
            'name': obj['name'],
            'email': obj['email']
        }

def fetch_loop(event):
    # from .models.models import VpnConnectionStatus 
    from vpn_manager.models.vpnconnectionstatus import VpnConnectionStatus
    time.sleep(4)
    while True:
        data = fetch_data()
        if data != False and data != "":
            client_status = convert_to_client_status(data)
            # print(client_status)
            for client in client_status:
                # id = g.curr_client_run[client['public_key']]['id']
                # client['peer_id'] = id
                if client['public_key'] not in g.curr_client_enabled:
                    update_list_client_enabled()
                
                if client['public_key'] not in g.curr_client_enabled:
                    continue
                
                # Nếu không có dữ liệu thì bỏ qua
                if client['curr_endpoint'] == '(none)': 
                    # client['curr_endpoint'] = ''
                    continue
                
                # Check xem lần fetch trước thì client này có chạy ?
                # print(g.curr_client_enabled)
                id = g.curr_client_enabled[client['public_key']]['id']
                
                id_str = str(id)
                if id_str not in g.last_client_status:
                    g.last_client_status[id_str] = {
                        'curr_endpoint': client['curr_endpoint'],
                        'rx': client['receive'],
                        'tx': client['transmit']
                    }
                    
                else:
                    if g.last_client_status[id_str]['curr_endpoint'] != client['curr_endpoint']:
                        client['type'] = 1
                        g.last_client_status[id_str]['curr_endpoint'] = client['curr_endpoint'] 
                    if g.last_client_status[id_str]['rx'] == client['receive']:  # TH client ngắt kết nối nhưng server vẫn gửi gói trống keep alive 
                        continue
                        
                    # Chỉ lưu số byte đã dùng tính từ lần fetch trước 
                    # print(client['transmit'], client['receive'])
                    tmp = client['receive']
                    client['receive'] -= g.last_client_status[id_str]['rx']
                    g.last_client_status[id_str]['rx'] = tmp
                    
                    tmp = client['transmit']
                    client['transmit'] -= g.last_client_status[id_str]['tx']
                    g.last_client_status[id_str]['tx'] = tmp
                    # print(client['transmit'], client['receive'])
                    
                
                del client['public_key']
                client['peer_id'] = id
                peerStatus = VpnConnectionStatus(**client)
                peerStatus.save()
                print("Success")
        time.sleep(30) # 60 minutes
        
# for save status peer each 1 hour
def create_daemon_thread():
    fetch_thread = threading.Thread(target=fetch_loop, args=(g.event,), daemon=True)
    fetch_thread.start()
