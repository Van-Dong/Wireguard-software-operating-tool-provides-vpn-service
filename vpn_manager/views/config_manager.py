from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import render
# from vpn_manager.models.models import GlobalSetting, Interface, VpnConnection
from vpn_manager.models.interface import Interface
from vpn_manager.models.globalsetting import GlobalSetting
from vpn_manager.models.vpnconnection import VpnConnection 
from django.forms.models import model_to_dict
from vpn_manager.serializers.serializers import GlobalSettingSerializer, InterfaceSerializer, VpnConnectionSerializer
from datetime import datetime
import wgconfig.wgexec as wgexec
from vpn_manager import global_variables as g
from vpn_manager.config import *
from vpn_manager.utils.util import get_ip_local, get_ip_public, enable_interface, stop_interface, sync_conf

import logging
# Tạo logger
logger = logging.getLogger(__name__)

# /global-settings/  GET POST
class GlobalSettingView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser, )

    # get
    def get(self, request):
        logger.info("[%s] [%s] - HTTP GET /global-settings/ 200 - Account %s access /global-settings/!", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username)
        try:
            global_settings = GlobalSetting.objects.last() 
            
            if global_settings is None: 
                global_settings = self.init_global_settings() 
            else:
                global_settings = model_to_dict(global_settings)

            if global_settings['dns_servers'] != '':
                global_settings['dns_servers'] = global_settings['dns_servers'].split(', ') 
            else:
                global_settings['dns_servers'] = []
            
            if global_settings['mtu'] is None:
                global_settings['mtu'] = ""
                
            return render(request, 'settings/global_settings.html', context={"data": global_settings})
        
        except Exception as e:
            # print('Error global-setting:' + str(e))
            return render(request, 'settings/global_settings.html')

    # update
    def post(self, request):
        request.data['dns_servers'] = ', '.join(request.data['dns_servers'])
        try:
            old_global_settings = GlobalSetting.objects.last()
            global_settings = GlobalSettingSerializer(old_global_settings, data=request.data)
        except Exception as e:
            logger.warning("[%s] [%s] - HTTP POST /global-settings/ 400 - Account %s updated system settings error %s with data: %s!", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username, str(e), request.data)
            return Response(data={"status": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)   

        if global_settings.is_valid():
            
            try:
                global_settings.save()
                # notify config change
                
                logger.info("[%s] [%s] - HTTP POST /global-settings/ 200 - Account %s updated system settings successfully with data: %s!", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username, request.data)
                return Response(data={"status" : True, "message": "Update system settings successfully!"}, status=status.HTTP_200_OK)
            except Exception as e:
                logger.warning("[%s] [%s] - HTTP POST /global-settings/ 400 - Account %s updated system settings error %s with data: %s!", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username, str(e), request.data)
                return Response(data={"status": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)          
            
        else:
            errors = global_settings.errors
            logger.warning("[%s] [%s] - HTTP POST /global-settings/ 400 - Account %s updated system settings error %s with data: %s!", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username, str(errors), request.data)
            errors['status'] = False
            return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)

    def init_global_settings(self):
        if DEFAULT_ENDPOINT_ADDRESS == "local":
            endpoint = get_ip_local() 
        else:
            endpoint = get_ip_public() 
        # need auto select endpoint
        global_settings = {
            "endpoint_address": endpoint,
            "dns_servers": ', '.join(DEFAULT_DNS),
            "persistent_keepalive": DEFAULT_PERSISTENT_KEEP_ALIVE,
            "mtu": DEFAULT_MTU,
            "table": DEFAULT_TABLE,
            "firewall_mark": DEFAULT_FIREWALL_MARK,
        }
    
        try:
            new_global_settings = GlobalSetting(**global_settings)
            new_global_settings.save()
            return global_settings
        except Exception as e: 
            return False

# /wg-server/interfaces/ GET POST
class InterfaceView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser, )

    def get(self, request):
        interfaces = Interface.objects.values()
        interface_serializered = InterfaceSerializer(interfaces, many=True)
        interfaces = interface_serializered.data
        # convert bad datetime format to beauty format
        for interface in interfaces:
            created_at = interface['created_at']
            created_at = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%fZ")
            created_at = created_at.strftime("%d/%m/%Y %H:%M:%S")
            interface['created_at'] = created_at
            
            updated_at = interface['updated_at']
            updated_at = datetime.strptime(updated_at, "%Y-%m-%dT%H:%M:%S.%fZ")
            updated_at = updated_at.strftime("%d/%m/%Y %H:%M:%S")
            interface['updated_at'] = updated_at
            
        logger.info("[%s] [%s] - HTTP GET /wg-server/interfaces/ 200 - Account %s access /wg-server/interfaces/!", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username)
        return render(request, 'main/wireguard_server.html', context={'interfaces': interfaces}, status=status.HTTP_200_OK)
    
    # update
    def post(self, request):
        request.data['addresses'] = ', '.join(request.data['addresses'])
        
        if request.data['public_key'] == '' and request.data['private_key'] == '':
            request.data['private_key'], request.data['public_key'] = wgexec.generate_keypair()
        elif request.data['public_key'] == '' or request.data['private_key'] == '':
            return Response(data={"status": False, "message": "Key pair not valid!"}, status=status.HTTP_400_BAD_REQUEST)
        
        interface = InterfaceSerializer(data=request.data)  # Dù old_interface = None vẫn chạy bình thường (--> create thay vì update)

        if interface.is_valid():
            try:
                # need check addresses (add sau)
                obj = interface.save()  # return obj save in database (have id)
                # notify config change
                if obj.enabled == True:
                    enable_interface(obj.id)
                
                # logger.info("[%s] [%s] - HTTP POST /wg-server/interfaces/ 200 - Account %s create wireguard interface successfully with data: %s!", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username, request.data)
                return Response(data={"status": True, "message": "Created wireguard interface successfully!"})
            except Exception as e:
                print(str(e))
                # logger.warning("[%s] [%s] - HTTP POST /wg-server/interfaces/ 400 - Account %s create wireguard interface failed, error %s with data: %s!", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username, str(e), request.data)
                return Response(data={"status": False, "message": "Created wireguard interface Failed!"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            errors = interface.errors
            # logger.warning("[%s] [%s] - HTTP POST /wg-server/interfaces/ 400 - Account %s updated wireguard interface failed, error %s with data: %s!", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username, errors, request.data)
            errors["status"] = False
            return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)
         
    def init_interface(self):
        private_key, public_key = wgexec.generate_keypair()
        interface = {
            "addresses": ", ".join(DEFAULT_SERVER_ADDRESS),
            "listen_port": DEFAULT_SERVER_PORT,
            "private_key": private_key,
            "public_key": public_key,
            "pre_up": "",
            "post_up": "",
            "pre_down": "",
            "post_down": ""
        }

        try:
            new_interface = Interface(**interface)
            new_interface.save()
            return interface
        except Exception as e:
            return False


# /wg-server/interface/<int:id>/
class ModifyInterfaceView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser, )
    
    def get(self, request, id):
        try:
            interface = Interface.objects.get(pk=id)
            # Chuyển đối tượng interface sang dictionary
            interface_dict = model_to_dict(interface)
            
            logger.info("[%s] [%s] - HTTP GET /wg-server/interface/%d/ 200 - Account %s get interface with id=%d successfully!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id)
            return Response(data=interface_dict, status=status.HTTP_200_OK)
        except Exception as e:
            logger.warning("[%s] [%s] - HTTP GET /wg-server/interface/%d/ 400 - Account %s get interface with id=%d failed!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id)
            return Response(data={"status": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    # update
    def post(self, request, id):
        request.data['addresses'] = ', '.join(request.data['addresses'])
        
        try:
            old_interface = Interface.objects.get(pk=id)
        except Exception as e:
            return Response(data={"status": False, "message": "Not find interface!"}, status=status.HTTP_400_BAD_REQUEST)
        
        if request.data['public_key'] == '' and request.data['private_key'] == '':
            request.data['private_key'], request.data['public_key'] = wgexec.generate_keypair()
        elif request.data['public_key'] == '' or request.data['private_key'] == '':
            return Response(data={"status": False, "message": "Key pair not valid!"}, status=status.HTTP_400_BAD_REQUEST)
        old_interface_name = old_interface.name
        interface = InterfaceSerializer(old_interface, data=request.data)

        if interface.is_valid():
            try:
                obj = interface.save() 
                if obj.enabled == True:
                    # print('enabled')
                    if old_interface_name != obj.name:
                        stop_interface(old_interface_name)
                    enable_interface(id)
                    
                else:
                    # print('disabled', old_interface_name)
                    stop_interface(old_interface_name)
                
                # logger.info("[%s] [%s] - HTTP POST /wg-server/interface/%d/ 200 - Account %s updated wireguard interface successfully with data: %s!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, request.data)
                return Response(data={"status": True, "message": "Updated wireguard interface successfully!"})
            except Exception as e:
                print(str(e))
                # logger.warning("[%s] [%s] - HTTP POST /wg-server/interface/%d/ 400 - Account %s updated wireguard interface failed, error %s with data: %s!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, str(e), request.data)
                return Response(data={"status": False, "message": "Updated wireguard interface Failed!"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            errors = interface.errors
            # logger.warning("[%s] [%s] - HTTP POST /wg-server/interface/%d/ 400 - Account %s updated wireguard interface failed, error %s with data: %s!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, errors, request.data)
            errors["status"] = False
            return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, id):
        try:
            interface = Interface.objects.get(pk=id)
            if interface.enabled == True:
                stop_interface(interface.name)
            interface.delete()
            
            # logger.info("[%s] [%s] - HTTP DELETE /wg-server/interface/%d/ 200 - Interface %s deleted interface id=%d successfully!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id)
            return Response(data={"status": True, "message": "Delete interface successfuly!"}, status=status.HTTP_200_OK)
        except Exception as e:
            # logger.warning("[%s] [%s] - HTTP DELETE /wg-server/interface/%d/ 400 - Interface %s deleted interface id=%d failed, error %s!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id, str(e))
            return Response(data={"status": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

# /wg-client/peer/  GET POST

class PeerView(APIView):
    permission_classes = (IsAuthenticated, )
    
    # list peer
    def get(self, request):
        clients = ""
        if request.user.is_staff:
            clients = VpnConnection.objects.values()
        else:
            clients = VpnConnection.objects.filter(user_id=request.user.id).values()
        client_serializered = VpnConnectionSerializer(clients, many=True)
        clients = client_serializered.data
        # convert bad datetime format to beauty format
        
        list_interface = Interface.objects.values('id', 'name')
        list_interface = list(list_interface)
        interfaces = {}
        for x in list_interface:
            interfaces[x['id']] = x['name']
        
        for client in clients:
            if client['interface_id'] != None:
                client['name_interface'] = interfaces[client['interface_id']]
            else:
                client['name_interface'] = ''
            
            created_at = client['created_at']
            created_at = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%fZ")
            created_at = created_at.strftime("%d/%m/%Y %H:%M:%S")
            client['created_at'] = created_at
            
            updated_at = client['updated_at']
            updated_at = datetime.strptime(updated_at, "%Y-%m-%dT%H:%M:%S.%fZ")
            updated_at = updated_at.strftime("%d/%m/%Y %H:%M:%S")
            client['updated_at'] = updated_at
              
        logger.info("[%s] [%s] - HTTP GET /wg-client/peer/ 200 - Account %s access /wg-client/peer/!", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username)
        return render(request, 'main/wireguard_client.html', context={'clients': clients, 'interfaces': interfaces}, status=status.HTTP_200_OK)
        
    # create new client
    def post(self, request):
        request.data['allocated_ips'] = ', '.join(request.data['allocated_ips'])
        request.data['allowed_ips'] = ', '.join(request.data['allowed_ips'])
        request.data['extra_allowed_ips'] = ', '.join(request.data['extra_allowed_ips'])
        request.data['user_id'] = request.user.id
        preshared_key = ''
        if request.data['preshared_key'] == '-': 
            request.data['preshared_key'] = ''
            preshared_key = '-'
            
        if request.data['interface_id'] == 0:
            del request.data['interface_id']
       
        peer = VpnConnectionSerializer(data=request.data)

        if peer.is_valid():
            data = peer.validated_data

            if data['preshared_key'] == "" and preshared_key == '':
                data['preshared_key'] = wgexec.generate_presharedkey()
            elif preshared_key == "-":
                data['preshared_key'] = ""
            if data['public_key'] == "":
                data['private_key'], data['public_key'] = wgexec.generate_keypair()
            else:
                data['private_key'] = ""
            
            try:
                obj = peer.save() # luu vao database
                
                
                if obj.interface_id == None or obj.enabled == False:
                    return Response(data={"status": True, "message": "Create vpn connection is successfully!"}, status=status.HTTP_200_OK) 
                
                # sync with interface
                try:
                    interface = Interface.objects.get(pk=obj.interface_id)
                    if interface.enabled == True:
                        result = sync_conf(interface.name, interface.id)
                        # print(result)
                        if result['status'] == False:
                            obj.enabled = False
                            obj.save()
                            return Response(data={"status": False, "message": "An error occurred when adding a peer to the wireguard interface!"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)         
                except Exception as e:
                    # print(str(e))
                    return Response(data={"status": False, "message": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
                    
                logger.info("[%s] [%s] - HTTP POST /wg-client/peer/ 200 - Account %s created new peer with data: %s!", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username, request.data)
                return Response(data=data, status=status.HTTP_200_OK)
            except Exception as e:
                print(str(e))
                logger.warning("[%s] [%s] - HTTP POST /wg-client/peer/ 400 - Account %s created new peer failed, error %s with data %s!", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username, str(e), request.data)
                return Response(data={"status": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        else:
            print
            errors = peer.errors
            # logger.warning("[%s] [%s] - HTTP POST /wg-client/peer/ 400 - Account %s created new peer failed, error %s with data %s!", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username, str(errors), request.data)
            errors["status"] = False
            return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)

# /peer/<int:id>/  GET POST(modify) DELETE
class ModifyPeerView(APIView):
    permission_classes = (IsAuthenticated,)
    
    # /peer/<int:id>/ GET
    def get(self, request, id):
        try:
            peer = VpnConnection.objects.get(pk=id)
            # Chuyển đối tượng Peer sang dictionary
            peer_dict = model_to_dict(peer)
            
            logger.info("[%s] [%s] - HTTP GET /peer/%d/ 200 - Account %s get client operator config with id=%d successfully!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id)
            return Response(data=peer_dict, status=status.HTTP_200_OK)
        except Exception as e:
            logger.warning("[%s] [%s] - HTTP GET /peer/%d/ 400 - Account %s get client operator config with id=%d failed!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id)
            return Response(data={"status": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # same create (don't have private_key)
    # /peer/<int:id>/ POST  - Modify client
    def post(self, request, id):
        
        # preprocess request data 
        request.data['allocated_ips'] = ', '.join(request.data['allocated_ips'])
        request.data['allowed_ips'] = ', '.join(request.data['allowed_ips'])
        request.data['extra_allowed_ips'] = ', '.join(request.data['extra_allowed_ips'])
        if request.data['preshared_key'] == "-":   # do field này chỉ cho phép min_length=44, max_length=44, allow blank => gặp vấn đề với '-'
            request.data['preshared_key'] = ""  
        elif request.data['preshared_key'] == "":
            request.data['preshared_key'] = wgexec.generate_presharedkey()
        
        # request.data['user_id'] = request.user.id
            
        old_peer = VpnConnection.objects.get(pk=id)
        peer = VpnConnectionSerializer(old_peer, data=request.data)

        if peer.is_valid():
            data = peer.validated_data
            if data['public_key'] == "":
                data['private_key'], data['public_key'] = wgexec.generate_keypair()
            else:
                if old_peer.public_key != data['public_key']: # study case: sử dụng public key do chính client tự sinh 
                    data['private_key'] = ""   
                else:
                    data['private_key'] = old_peer.private_key
            try:
                obj = peer.save()
                
                if obj.interface_id == None or obj.enabled == False:
                    return Response(data={"status": True, "message": "Update client successfuly!"}, status=status.HTTP_200_OK)
                    
                # sync with interface
                try:
                    interface = Interface.objects.get(pk=obj.interface_id)
                    if interface.enabled == True:
                        result = sync_conf(interface.name, interface.id)
                        # print(result)
                        if result['status'] == False:
                            return Response(data={"status": False, "message": "An error occurred when delete a peer to the wireguard interface!"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)         
                except Exception as e:
                    # print(str(e))
                    return Response(data={"status": False, "message": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
                
                
                logger.info("[%s] [%s] - HTTP POST /peer/%d/ 200 - Account %s updated client id=%d successfully with data: %s!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id, request.data)
                return Response(data={"status": True, "message": "Updated client successfully!"}, status=status.HTTP_200_OK)
            except Exception as e:
                
                logger.warning("[%s] [%s] - HTTP POST /peer/%d/ 400 - Account %s updated client id=%d failed, error %s with data: %s!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id, str(e), request.data)
                return Response(data={"status": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        else:
            errors = peer.errors
            logger.warning("[%s] [%s] - HTTP POST /peer/%d/ 400 - Account %s updated client id=%d failed, error %s with data: %s!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id, str(errors), request.data)
            errors["status"] = False
            return Response(data=errors, status=status.HTTP_400_BAD_REQUEST)

    # /peer/<int:id>/ DELETE
    def delete(self, request, id):
        try:
            peer = VpnConnection.objects.get(pk=id)
            peer.delete()
            
            if peer.interface_id == None or peer.enabled == False:
                return Response(data={"status": True, "message": "Delete client successfuly!"}, status=status.HTTP_200_OK)
                
                # sync with interface
            try:
                interface = Interface.objects.get(pk=peer.interface_id)
                if interface.enabled == True:
                    result = sync_conf(interface.name, interface.id)
                    # print(result)
                    if result['status'] == False:
                        return Response(data={"status": False, "message": "An error occurred when delete a peer to the wireguard interface!"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)         
            except Exception as e:
                # print(str(e))
                return Response(data={"status": False, "message": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
                
            
            logger.info("[%s] [%s] - HTTP DELETE /peer/%d/ 200 - Account %s deleted client id=%d successfully!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id)
            return Response(data={"status": True, "message": "Delete client successfuly!"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.warning("[%s] [%s] - HTTP DELETE /peer/%d/ 400 - Account %s deleted client id=%d failed, error %s!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id, str(e))
            return Response(data={"status": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# /enable/peer/<int:id> POST
class EnablePeerView(APIView):
    permission_classes = (IsAuthenticated, )
    
    def post(self, request, id):
        try:
            peer = VpnConnection.objects.get(pk=id)
            if peer.enabled == False:
                peer.enabled = True
                peer.save()
                # Nếu peer có liên kết với interface 
                if peer.interface_id == None:
                    return Response(data={"status": False, "message": "Enable client is failed!"}, status=status.HTTP_400_BAD_REQUEST) 
                # sync with interface
                try:
                    interface = Interface.objects.get(pk=peer.interface_id)
                    if interface.enabled == True:
                        result = sync_conf(interface.name, interface.id)
                        # print(result)
                        if result['status'] == False:
                            peer.enabled = False
                            peer.save()
                            return Response(data={"status": False, "message": "An error occurred when adding a peer to the wireguard interface!"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)         
                except Exception as e:
                    # print(str(e))
                    return Response(data={"status": False, "message": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
                    
            logger.info("[%s] [%s] - HTTP POST /enable/peer/%d/ 200 - Account %s enabled client id=%d successfully!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id)
            return Response(data={"status": True, "message": "Enable client is successfully!"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.warning("[%s] [%s] - HTTP POST /enable/peer/%d/ 400 - Account %s enabled client id=%d failed!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id)
            return Response(data={"status": False, "message": "Enable client is failed!"}, status=status.HTTP_400_BAD_REQUEST)
     
# /disable/peer/<int:id> POST
class DisablePeerView(APIView):
    permission_classes = (IsAuthenticated, )
    
    def post(self, request, id):
        try:
            peer = VpnConnection.objects.get(pk=id)
            if peer.enabled == True:
                peer.enabled = False
                peer.save()
                if peer.interface_id == None:
                    return Response(data={"status": True, "message": "Disable client is successfully!"}, status=status.HTTP_200_OK)
                    # sync with interface
                try:
                    interface = Interface.objects.get(pk=peer.interface_id)
                    if interface.enabled == True:
                        result = sync_conf(interface.name, interface.id)
                        # print(result)
                        if result['status'] == False:
                            peer.enabled = True
                            peer.save()
                            return Response(data={"status": False, "message": "An error occurred when adding a peer to the wireguard interface!"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)         
                except Exception as e:
                    # print(str(e))
                    return Response(data={"status": False, "message": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 

            logger.info("[%s] [%s] - HTTP POST /disable/peer/%d/ 200 - Account %s disabled client id=%d successfully!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id)
            return Response(data={"status": True, "message": "Disable client is successfully!"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.warning("[%s] [%s] - HTTP POST /disable/peer/%d/ 400 - Account %s disabled client id=%d failed!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id)
            return Response(data={"status": False, "message": "Disable client is failed!"}, status=status.HTTP_400_BAD_REQUEST)

# /enable/interface/<int:id> POST
class EnableInterfaceView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser, )
    
    def post(self, request, id):
        try:
            interface = Interface.objects.get(pk=id)
            if interface.enabled == False:
                result = enable_interface(id)
                if result['status'] == True:
                    interface.enabled = True
                    interface.save()
                else: 
                    return Response(data={"status": False, "message": result['message']}, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info("[%s] [%s] - HTTP POST /enable/interface/%d/ 200 - Account %s enabled interface id=%d successfully!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id)
            return Response(data={"status": True, "message": "Enable interface is successfully!"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.warning("[%s] [%s] - HTTP POST /enable/interface/%d/ 400 - Account %s enabled interface id=%d failed!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id)
            return Response(data={"status": False, "message": "Enable interface is failed!"}, status=status.HTTP_400_BAD_REQUEST)
    
# /disable/interface/<int:id> POST
class DisableInterfaceView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser, )
    
    def post(self, request, id):
        try:
            interface = Interface.objects.get(pk=id)
            if interface.enabled == True:
                result = stop_interface(interface.name)
                if result['status'] == True:
                    interface.enabled = False
                    interface.save()
                else:
                    return Response(data=result, status=status.HTTP_400_BAD_REQUEST)
            
            logger.info("[%s] [%s] - HTTP POST /disable/interface/%d/ 200 - Account %s disabled interface id=%d successfully!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id)
            return Response(data={"status": True, "message": "Disable interface is successfully!"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.warning("[%s] [%s] - HTTP POST /disable/interface/%d/ 400 - Account %s disabled interface id=%d failed!", request.META['REMOTE_ADDR'], request.auth['jti'], id, request.user.username, id)
            return Response(data={"status": False, "message": "Disable interface is failed!"}, status=status.HTTP_400_BAD_REQUEST)
