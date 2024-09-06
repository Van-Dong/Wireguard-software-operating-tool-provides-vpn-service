from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.http import HttpResponse
import wgconfig.wgexec as wgexec

import os
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from vpn_manager import global_variables as g
from vpn_manager.utils.util import get_list_ip, create_client_config, enable_interface, get_name_interface_wireguard, stop_interface, is_valid_ipv4_interface
from vpn_manager.config import *
from vpn_manager.models.interface import Interface
from vpn_manager.models.vpnconnection import VpnConnection
from ipaddress import ip_network
from django.forms.models import model_to_dict

import logging
# Tạo loggerVpnConnection
logger = logging.getLogger(__name__)

# /wg-server/suggest-ip/ POST
class SuggestIpView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser, )
    
    def post(self, request):
        list_ip = get_list_ip()
        return Response(data={"status": True, "data": list_ip}, status=status.HTTP_200_OK)

# /wg-server/keypair/ POST
class GenKeyPairView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser, )

    def post(self, request):  # chỉ generate key pair cho browser, chứ chưa lưu vào csdl. Nhấn nút Save mới lưu một thể vào CSDL
        try:
            private_key, public_key = wgexec.generate_keypair()
            
            logger.info("[%s] [%s] - HTTP POST /wg-server/keypair/ 200 - Account %s generate keypair successfully!", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username)
            return Response(data={'status': True, 'private_key': private_key, 'public_key': public_key}, status=status.HTTP_200_OK)
        except Exception as e:
            
            logger.warning("[%s] [%s] - HTTP POST /wg-server/keypair/ 400 - Account %s updated system settings error %s!", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username, str(e))
            return Response(data={"status": False, "message": "Generate keypair falied!"}, status=status.HTTP_400_BAD_REQUEST)


# /send-email/
class SendEmailView(APIView):
    permission_classes = (IsAuthenticated, )
    
    def post(self, request):
        # EmailMessage có thể định dạng nội dung thành <html>
        email_from = os.getenv('EMAIL_HOST_USER')
        subject = 'Send wireguard client config for you'
        message = ''
        recipient_list = []
        
        clientid = int(request.data['clientid'])
        recipient_email = request.data['email']
        
        try:
            validate_email(recipient_email)
            recipient_list.append(recipient_email)
        except ValidationError as e:
            return Response(data={"status": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        result = create_client_config(clientid)
        if result == False:
            return Response(data={"status": False, "message": "An error occurred!"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            email = EmailMessage(subject, message, email_from, recipient_list)
            email.attach(f'{result[1]}.conf', result[0], 'text/plain')
            sent_count = email.send(fail_silently=False) 
            if sent_count == 1:
                return Response(data={"status": True, "message": "Send email successfully!"})
            else:
                return Response(data={"status": False, "message": "Send email failed!"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(data={"status": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
# /download/<int:id>/ GET
class DownloadView(APIView):
    permission_classes = (IsAuthenticated, )

    def get(self, request, id):
        client_data = create_client_config(id)
        if client_data == False:
            logger.warning("[%s] [%s] - HTTP GET /download/%d/ 400 - Account %s download client config id=%d failed!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id)
            return Response(data={'status': False, 'message': 'An error occurred!'}, status=status.HTTP_400_BAD_REQUEST)
        response = HttpResponse(client_data[0], content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{client_data[1]}.conf"'
        
        logger.info("[%s] [%s] - HTTP GET /download/%d/ 200 - Account %s download client config id=%d successfully!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id)
        return response

# /clientconfig/<int:id>/ GET  - for QR Code
class ClientConfigView(APIView):
    permission_classes = (IsAuthenticated, )
    
    def get(self, request, id):
        client_config = create_client_config(id)
        if client_config == False:
            logger.warning("[%s] [%s] - HTTP GET /clientconfig/%d/ 400 - Account %s get client config id=%d failed!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id)
            return Response(data={'status': False, 'message': "Can't get client data!"}, status=status.HTTP_400_BAD_REQUEST)
        
        logger.info("[%s] [%s] - HTTP GET /clientconfig/%d/ 200 - Account %s get client config id=%d successfully!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id)
        return Response(data={'status': True, 'client_config': client_config[0]})
              

# /wg-client/list-interface/
class ListInterfaceView(APIView):
    permission_classes = (IsAuthenticated, )
    def post(self, request):
        interfaces = Interface.objects.values('name', 'id', 'addresses') # return kieu dict
        interfaces = list(interfaces)
        return Response(data={"status": True, "data": interfaces})

# /wg-server/detail/<int:id>/
class DetailInterfaceView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)
    
    def get(self, request, id):
        data = self.get_detail_interface(id)
        if data == None:
            return Response(data={'status': False, 'message': 'Not found Wg network interface!'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(data={'status': True, 'data': data})
        
    def get_detail_interface(self, id):
        interface = ''
        try:
            interface = Interface.objects.get(pk=id) 
            interface_dict = model_to_dict(interface)
            
            interface_dict['created_at'] = interface.created_at.strftime("%d/%m/%Y %H:%M:%S")
            interface_dict['updated_at'] = interface.updated_at.strftime("%d/%m/%Y %H:%M:%S")
        except Exception as e:
            return None
        list_vpnconnection = VpnConnection.objects.filter(interface_id=id).values_list('name', 'enabled')
        list_vpnconnection = list(list_vpnconnection)   
        interface_dict['list_vpnconnection'] = list_vpnconnection
        interface_dict['addresses'] = interface_dict['addresses'].split(', ')
        return interface_dict

# /wg-server/suggest-interface/ POST
class SuggestInterfaceView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)
    
    def post(self, request):
        listen_ports = Interface.objects.values_list('listen_port', flat=True)
        ports_list = list(listen_ports)
        port = self.suggest_listen_port(ports_list)
        
        list_address = Interface.objects.values_list('addresses', flat=True)
        list_address = list(list_address)
        ip_list = []
        for x in list_address:
            ip_list.extend(x.split(', ')) 
        ip = self.suggest_addresses(ip_list)
        
        list_name = Interface.objects.values_list('name', flat=True)
        list_name = list(list_name) 
        name = self.suggest_name_interface(list_name) 
        
        # if USED_NAT == True:
        #     post_up = "iptables -t nat -A POSTROUTING -o name_public_interface -j MASQUERADE;"
        #     pre_down = "iptables -t nat -D POSTROUTING -o name_public_interface -j MASQUERADE;"
        post_up = f"iptables -I INPUT 1 -p udp --dport {port} -j ACCEPT;"
        pre_down = f"iptables -D INPUT -p udp --dport {port} -j ACCEPT;"
        
        interface = {
            'name': name,
            'listen_port': port,
            'addresses': ip,
            'pre_up': '',
            'post_up': post_up,
            'pre_down': pre_down,
            'post_down': '',
        }
        
        return Response(data={"status": True, "data": interface})
          
    
    def suggest_listen_port(self, list_port): 
        set_port = set(list_port)
        for port in range(51820, 65535):
            if port not in set_port:
                return port
        return 0
    
    def suggest_addresses(self, list_address):
        
        used_subnets = set()
        for ip in list_address:
            if is_valid_ipv4_interface(ip):
                parts = ip.split('.')
                subnet = parts[0] + '.' + parts[1] + '.' + parts[2] 
                used_subnets.add(subnet)
        for z in range(256):
            subnet = f"10.252.{z}"
            if subnet not in used_subnets:
                return [f"{subnet}.1/24"]
        return []
    
    def suggest_name_interface(self, list_name):
        used_name = set(list_name)
        for x in range(256):
            name = f"wg{x}"
            if name not in used_name:
                return name
        return ''

# /suggest-vpnconnection/ GET POST
class SuggestVpnConnectionView(APIView):
    permission_classes = (IsAuthenticated, )
    
    def get(self, request):
        interface_id = request.GET.get('interface_id')
        if interface_id == None:
            return Response(data={'status': False, 'message': 'Not found interface id!'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            interface_id = int(interface_id)
        except:
            return Response(data={'status': False, 'message': 'Interface id must be number!'}, status=status.HTTP_400_BAD_REQUEST)
        
        result = self.suggest_ips(interface_id)
        return Response(data={'status': True, 'data': result}, status=status.HTTP_200_OK)
    
    def post(self, request):
        interfaces = Interface.objects.values('name', 'id', 'addresses') # return kieu dict
        interfaces = list(interfaces)
        if interfaces == []:
            return Response(data={"status": False, "message": "Could not find any interfaces"}, status=status.HTTP_204_NO_CONTENT)
        
        suggest_data = self.suggest_ips(interfaces[0]['id'])
        suggest_data['interfaces'] = interfaces
        return Response(data={'status': True, 'data':suggest_data}, status=status.HTTP_200_OK)
        
             
    def suggest_allocated_ip(self, interface_ip, list_used_ip):
        try:
            interface_network = ip_network(interface_ip, strict=False)
            
            cur_ip = interface_network.network_address + 1
            while cur_ip in interface_network and str(cur_ip) in list_used_ip:
                cur_ip += 1
                
            if cur_ip in interface_network:
                return str(cur_ip) + '/32'
        except Exception as e:
            print(e)
        
        return None
    
    def suggest_ips(self, interface_id):
        
        interface_ips = Interface.objects.get(pk=interface_id).addresses.split(', ')
        
        list_vpnconnection_ip = VpnConnection.objects.filter(interface_id=interface_id).values_list('allocated_ips', flat=True) 
        temp = []
        for ip in list_vpnconnection_ip:
            temp.extend(ip.split(', '))
        
        list_used_ip = set()
        for ip in temp:
            list_used_ip.add(ip.split('/')[0])  # remove subnet mask
        
        for ip in interface_ips:
            list_used_ip.add(ip.split('/')[0])  # add interface ip
        
        allocated_ip = ''
        allowed_ip = '0.0.0.0/0'
        for ip in interface_ips:
            result = self.suggest_allocated_ip(ip, list_used_ip)
            if result != None:
                allocated_ip = result
                if is_valid_ipv4_interface(ip):
                    allowed_ip = ip.split('/')[0] + '/32'
                else:
                    allowed_ip = ip.split('/')[0] + '/128'
                break
        
        suggest_data = {
            'allocated_ip': [allocated_ip],
            'allowed_ip': [allowed_ip],
        }
        return suggest_data