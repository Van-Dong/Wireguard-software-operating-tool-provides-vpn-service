from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from .views.authentication import LoginView, LogoutView, CustomTokenObtainPairView
from .views.user_manager import UserView, ProfileView
from .views.config_manager import GlobalSettingView, InterfaceView, ModifyInterfaceView, EnableInterfaceView, DisableInterfaceView
from .views.config_manager import PeerView, ModifyPeerView, EnablePeerView, DisablePeerView
from .views.backup_restore import BackupView, RecoverView, ImportView, ExportView
from .views.monitor import MonitorView, DashboardView, StatisticVPNConnectionView
from .views.helper import GenKeyPairView, SuggestIpView, ClientConfigView, DownloadView, SendEmailView, SuggestInterfaceView, DetailInterfaceView, SuggestVpnConnectionView, ListInterfaceView

router = DefaultRouter()
router.register('', UserView) # UserView

urlpatterns = [

    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),  # only return access token 
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout' ), # logout, remove access token
    
    # profile/
    path('profile/', ProfileView.as_view(), name='profile'),
    
    # wg-server/  - render html
    
    path('global-settings/', GlobalSettingView.as_view(), name='global-settings'),
    path('wg-server/interfaces/', InterfaceView.as_view(), name='inteface'),
    path('wg-server/interface/<int:id>/', ModifyInterfaceView.as_view(), name='modify-inteface'),
    path('enable/interface/<int:id>/', EnableInterfaceView.as_view(), name='enable interface'),
    path('disable/interface/<int:id>/', DisableInterfaceView.as_view(), name='disable interface'),
    
    path('wg-client/peer/', PeerView.as_view(), name='peer'),
    path('peer/<int:id>/', ModifyPeerView.as_view(), name='modify_peer'),
    path('enable/peer/<int:id>/', EnablePeerView.as_view(), name='enable peer'),
    path('disable/peer/<int:id>/', DisablePeerView.as_view(), name='disable peer'),
    path('suggest-vpnconnection/', SuggestVpnConnectionView.as_view(), name='suggest-vpnconnection'),
    
    
    path('wg-client/list-interface/', ListInterfaceView.as_view(), name='list-interfafce'),
    path('wg-server/keypair/', GenKeyPairView.as_view(), name='keypair'),
    path('wg-server/suggest-ip/', SuggestIpView.as_view(), name='suggest-ip'),
    path('wg-server/suggest-interface/', SuggestInterfaceView.as_view(), name='suggest-interface'),
    path('wg-server/detail/<int:id>/', DetailInterfaceView.as_view(), name='detail-interface'), 
    path('download/<int:id>/', DownloadView.as_view(), name='download'),
    path('clientconfig/<int:id>/', ClientConfigView.as_view(), name='clientconfig'),
    path('send-email/', SendEmailView.as_view(), name='send-email'),
    
    # GET  POST backup/
    path('backup/', BackupView.as_view(), name='backup'),
    path('recover/<str:time>/', RecoverView.as_view(), name='recover'),
    path('export/<str:model_name>/', ExportView.as_view(), name='export'),
    re_path(r'^import/(?P<model_name>|user|vpnconnection|interface|globalsetting|all)/$', ImportView.as_view(), name='import'),
    
    
    path('monitor/', MonitorView().as_view(), name='monitor'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('statistic-peer/<int:id>/', StatisticVPNConnectionView.as_view(), name='statistic-peer'),

    # path('/', include(router.urls), name='user'),
    path('users/', include(router.urls)),  
]
