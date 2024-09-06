from vpn_manager import global_variables as g
import json
import signal

# Hàm để lưu biến vào file JSON
def save_variables():
    my_variables = {
        'curr_client_enabled': g.curr_client_enabled,   
        'is_run': g.is_run, 
        'last_client_status': g.last_client_status,
    }
    with open('vpn_manager/backup/temp/tmp_variables.json', 'w') as f:
        json.dump(my_variables, f, indent=4)
    print("Variables saved.")

# Xử lý các tín hiệu như SIGTERM và SIGINT
def handle_signal(signum, frame):
    save_variables()
    exit(0)

# chú ý: nếu không chạy server dưới dạng --noreload thì sẽ bị có 2 luồng --> chạy hàm 2 lần
def handle_stop_server():
    # Đăng ký hàm xử lý cho các tín hiệu
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)  # CTRL + C

# Tải lại biến từ file JSON khi server khởi động
def handle_start_server():
    try:
        with open('vpn_manager/backup/temp/tmp_variables.json', 'r') as f:
            my_variables = json.load(f)
            g.curr_client_enabled = my_variables['curr_client_enabled']   
            g.is_run = my_variables['is_run']
            g.last_client_status = my_variables['last_client_status']
    except FileNotFoundError:
        print("No saved variables found.")

