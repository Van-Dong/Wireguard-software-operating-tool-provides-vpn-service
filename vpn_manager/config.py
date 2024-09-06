
# Environment Variables Config
DEFAULT_USERNAME                        = "admin"
DEFAULT_PASSWORD                        = "admin"
DEFAULT_IS_ADMIN                        = True
DEFAULT_SERVER_ADDRESS                  = ["10.252.1.1/24"]
DEFAULT_SERVER_PORT                     = 51820
DEFAULT_ENDPOINT_ADDRESS                = "local"  # local or public
DEFAULT_DNS                             = ["1.1.1.1"]
DEFAULT_MTU                             = 1450
DEFAULT_PERSISTENT_KEEP_ALIVE           = 15
DEFAULT_FIREWALL_MARK                   = "0xca6c" # 51820
DEFAULT_TABLE                           = "auto"
DEFAULT_CONFIG_FILE_PATH                = "wg0"
MAX_UPLOAD_FILE_SIZE                    = 3*1024*1024  # 3MB
USED_NAT                                = True



##
CONFIG_JSON_FOLDER_PATH = "vpn_manager/config/"
BACKUP_FOLDER_PATH = 'vpn_manager/backup/'
LIST_MODEL = ['vpn_manager.user', 'vpn_manager.vpnconnection', 'vpn_manager.interface', 'vpn_manager.globalsetting', 'vpn_manager.vpnconnectionstatus']
config_has_changed = True