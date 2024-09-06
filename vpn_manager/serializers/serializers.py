from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from vpn_manager.models.user import User
from vpn_manager.models.interface import Interface
from vpn_manager.models.globalsetting import GlobalSetting
from vpn_manager.models.vpnconnection import VpnConnection
from vpn_manager.utils.util import is_valid_ip, is_valid_ipv4_interface, is_valid_ipv6_interface, check_is_overlap_network
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

# import datetime

# required: endpoint_address, config_file_path
class GlobalSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = GlobalSetting
        fields = '__all__'
        
    # invalid -> return error, Valided --> return value
    # method is_valid() sẽ use phương thức này để xác thực. 
    # (vì vậy không cần try / except đâu, trong phương thức is_valid() xử lý rồi) 
    def validate_endpoint_address(self, data):
        # endpoint_address
        if not is_valid_ip(data):
            raise serializers.ValidationError("Enpoint address value is invalid!")
        return data
    
    def validate_dns_servers(self, data):
        # dns_servers
        if data == '':
            return data
        data_list = data.split(', ')
        for dns_ip in data_list:
            if not is_valid_ip(dns_ip):
                raise serializers.ValidationError("DNS address value is invalid!")
        return data
    
    def validate_table(self, data):
        # table
        if data not in ["auto", "off", ""]:
            raise serializers.ValidationError("Table value is invalid!")
        return data
    

# Addresses ở dạng string 
class InterfaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interface
        fields = '__all__'
        
    def validate_addresses(self, data):
        # address
        # if len(data) == 0:
        #     raise serializers.ValidationError("Server interface addresses mustn't empty!")

        parsed_data = data.split(', ')  # convert string to list
        for address in parsed_data:
            if not is_valid_ipv4_interface(address) and not is_valid_ipv6_interface(address):
                raise serializers.ValidationError("Ip address interface is invalid!")
        
        # validate unique subnet
        list_address = Interface.objects.values_list('addresses', flat=True)
        list_ip = []
        for x in list_address:
            list_ip.extend(x.split(', '))
                
        for address in parsed_data:
            result, overlap = check_is_overlap_network(address, list_ip) 
            if result == True:
                raise serializers.ValidationError(f"Ip address interface is overlap with subnet {overlap}!")
        
        return data
    
    
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Tùy chỉnh dữ liệu trước khi nó được trả về
        ret['addresses'] = ret['addresses'].split(', ')
        return ret
    
    
class VpnConnectionSerializer(serializers.ModelSerializer):
    # user = serializers.PrimaryKeyRelatedField(read_only=True)
    user_id = serializers.IntegerField(write_only=True, required=False) 
    interface_id = serializers.IntegerField(default=None)
    
    class Meta:
        model = VpnConnection
        # fields = '__all__'
        fields = ['id', 'name', 'email', 'interface_id', 'user_id', 'allocated_ips', 'private_key', 'public_key', 'preshared_key', 'allowed_ips', 'endpoint', 
                  'extra_allowed_ips', 'use_server_dns', 'enabled', 'additional_notes', 'created_at', 'updated_at']
        # exclude = ('allocated_ips',)
    # def create(self, validated_data):
    #     pass
    
    def validate_allocated_ips(self, data):
        # address
        parsed_data = data.split(', ')  # convert string to list
        for address in parsed_data:
            if not is_valid_ipv4_interface(address) and not is_valid_ipv6_interface(address):
                raise serializers.ValidationError("Allocated ip is invalid!")

        return data
    
    def validate_allowed_ips(self, data):
        parsed_data = data.split(', ')  # convert string to list
        for address in parsed_data:
            if not is_valid_ipv4_interface(address) and not is_valid_ipv6_interface(address):
                raise serializers.ValidationError("Allowed ip is invalid!")
        return data
    
    def validate_extra_allowed_ips(self, data):
        if data == "":   # do '' khi parse sang list sẽ thành ['']
            return data
        parsed_data = data.split(', ')  # convert string to list
        for address in parsed_data:
            if not is_valid_ipv4_interface(address) and not is_valid_ipv6_interface(address):
                raise serializers.ValidationError("Allowed ip is invalid!")
        return data
    
    def validate(self, data):
        # validate allocated_ips not overlap with Wg interface subnet
        allocated_ips = data['allocated_ips'].split(', ')
        
        list_interface_address = Interface.objects.exclude(pk=data['interface_id']).values_list('addresses', flat=True)
        list_interface_ip = []
        for x in list_interface_address:
            list_interface_ip.extend(x.split(', '))
            
        for address in allocated_ips:
            result, overlap = check_is_overlap_network(address, list_interface_ip) 
            if result == True:
                raise serializers.ValidationError(f"Allocated ips is overlap with subnet of interface address: {overlap}!")
        
        # allocated_ips must difference assigned ips
        assigned_interface_ips = Interface.objects.filter(pk=data['interface_id']).values_list('addresses', flat=True).first()
        assigned_interface_ips = assigned_interface_ips.split(', ')
        ips_set = set()
        for ip in assigned_interface_ips:
            ips_set.add(ip.split('/')[0])
            
        for ip in allocated_ips:
            if ip.split('/')[0] in ips_set:
                raise serializers.ValidationError(f"Allocated ip {ip} overlaps with the interface's ip address")
            
        return data
        
    
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        # Tùy chỉnh dữ liệu trước khi nó được trả về
        ret['allocated_ips'] = ret['allocated_ips'].split(', ')
        ret['allowed_ips'] = ret['allowed_ips'].split(', ')
        if ret['extra_allowed_ips'] != '':
            ret['extra_allowed_ips'] = ret['extra_allowed_ips'].split(', ')
        else:
            ret['extra_allowed_ips'] = []
        return ret
    


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'email', 'is_staff']
        extra_kwargs = {
            'password': {'write_only': True}
        }
        # fields = ['username', 'email', 'password']
    
    def create(self, validated_data):
        data = validated_data.copy()

        user = User(**data)  # syntax **kwargs to giai nen cac cap key-value trong data
        user.set_password(user.password)
        user.save()

        return user
    
    
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims here if needed
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data.pop('refresh', None)  # Remove refresh token from response
        return data
    