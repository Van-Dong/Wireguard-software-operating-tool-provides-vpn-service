curr_client_enabled = {}  # public key and id  
is_run = '' # true or false  
last_client_status = {}
# thread_id = ''

from threading import Event
event = Event() # khi khởi tạo thì flag được đặt là clear 
# event.set() 
# event.wait()
# event.clear() # đặt về trạng thái chưa đặt set ==> nếu gặp event.wait() thì phải đợi cho đến khi event.set() được gọi 
# thread_t.join() # chawnj thread hiện tại cho đến khi thread_t thực thi xong