from django.apps import AppConfig



class VpnManagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'vpn_manager'
    
    def ready(self):
        from .background_task.tasks import create_thread_monitor
        from .background_task.lifecycle_tasks import handle_start_server, handle_stop_server
        from .background_task.scheduler import create_daemon_thread
        create_thread_monitor()
        create_daemon_thread()
        
        # ## Tín đăng ký tín hiệu kết thúc để lưu các biến tạm thời vào:
        # handle_stop_server()
        # ## load tmp_variable khi server start.
        # handle_start_server()
