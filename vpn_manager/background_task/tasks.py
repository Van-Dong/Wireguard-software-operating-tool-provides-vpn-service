import threading, time, os, subprocess 
from vpn_manager import global_variables as g
from django_eventstream import send_event  



# chuyển đổi dữ liệu dạng string sang dạng object 
def parse_dump_data(wg_dump):
    lines = wg_dump.strip().split('\n')
    
    # Define a list to hold parsed data
    # parsed_data = []
    parsed_data = {}
    
    # Process each line
    curr_interface = ''
    for line in lines:
        fields = line.split('\t')
        if fields[0] == curr_interface:
            entry = {
                # "interface": fields[0],
        	    "public_key": fields[1],
                'name': g.curr_client_enabled[fields[1]]['name'] if fields[1] in g.curr_client_enabled else '',
                'email': g.curr_client_enabled[fields[1]]['email'] if fields[1] in g.curr_client_enabled else '',
        	    "preshared_key": fields[2],
        	    "endpoint": fields[3],
        	    "allowed_ips": fields[4] if len(fields) > 4 else None,
        	    "latest_handshake": fields[5] if len(fields) > 5 else None, # number 
        	    "transfer_rx": fields[6] if len(fields) > 6 else None,  # number 
        	    "transfer_tx": fields[7] if len(fields) > 7 else None,  # number
        	    "persistent_keepalive": fields[8] if len(fields) > 8 else None,  # off or number
            }
            parsed_data[curr_interface]['peers'].append(entry)
        else:
            curr_interface = fields[0]
            parsed_data[curr_interface] = {}
            parsed_data[curr_interface]['peers'] = []
            parsed_data[curr_interface]['private_key'] = fields[1]
            parsed_data[curr_interface]['public_key'] = fields[2]
            parsed_data[curr_interface]['listen_port'] = fields[3]
            parsed_data[curr_interface]['fwmark'] = fields[4]
            
    return parsed_data

# lấy dữ liệu từ wg dump rồi chuyển đổi sang object
def get_wg_dump_data():
    sudo_password = os.getenv('PASSWORD')
    command = f"wg show all dump".split()
    cmd1 = subprocess.Popen(['echo',sudo_password], stdout=subprocess.PIPE)
    cmd2 = subprocess.Popen(['sudo', '-S'] + command, stdin=cmd1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    cmd2.wait()
    stdout, stderr = cmd2.communicate()
    if cmd2.returncode == 0:
        # success: nếu không có wg interface nào chạy thì trả về  ""
        wg_dump = stdout.decode('utf-8')
        if wg_dump !=  "":
            parsed_data = parse_dump_data(wg_dump)
            # print(parsed_data)
            return parsed_data
        else:
            return ""
    else:
        return False

# Hàm gửi dữ liệu wg dump all thời gian thực cho client 
def event_loop():
    # track_log_by_subprocess()
    while True:
        data = get_wg_dump_data()
        if data == False:     
            send_event('monitor', 'message', {'status': False})
        elif data == '':
            send_event('monitor', 'message', {'status': True, 'data': ''})
        else:
            # print(data)
            # for interface in data:
            #     for client in data[interface]['peers']:
            #         if client['public_key'] in g.curr_client_run:
            #             client.update(g.curr_client_run[client['public_key']])  ## vấn đề lấy name và email của VPN Connection
                
            send_event('monitor', 'message', {'status': True, 'data': data})

            
        time.sleep(5)  # 4s

# Tạo và khởi động luồng xử lý sự kiện
def create_thread_monitor():
    event_thread = threading.Thread(target=event_loop, daemon=True)
    event_thread.start()
