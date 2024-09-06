from django.contrib import admin
from vpn_manager.models.globalsetting import GlobalSetting
from vpn_manager.models.interface import Interface
from vpn_manager.models.user import User
from vpn_manager.models.vpnconnection import VpnConnection
from vpn_manager.models.vpnconnectionstatus import VpnConnectionStatus

# Register your models here.
admin.site.register(GlobalSetting)
admin.site.register(Interface)
admin.site.register(User)
admin.site.register(VpnConnection)
admin.site.register(VpnConnectionStatus)

