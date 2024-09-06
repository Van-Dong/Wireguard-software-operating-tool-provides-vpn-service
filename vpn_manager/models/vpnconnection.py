from django.db import models
from django.core.validators import MinLengthValidator, MinValueValidator, MaxValueValidator
from .user import User
from .interface import Interface


class VpnConnection(models.Model):
    name = models.CharField(unique=True, max_length=50)
    email = models.EmailField(blank=True, max_length=50)
    interface = models.ForeignKey(Interface, null=True, on_delete=models.SET_NULL)
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    
    # allocated_ips= models.ListField(child=models.CharField(min_length=9))  # address interface for client, accept ipv6
    allocated_ips = models.CharField(unique=True, max_length=255)
    private_key = models.CharField(blank=True, max_length=44, validators=[MinLengthValidator(44)])  # for client config
    public_key = models.CharField(blank=True, max_length=44, validators=[MinLengthValidator(44)])  # for server config, user filled --> don't generate private_key
    preshared_key = models.CharField(blank=True, max_length=44, validators=[MinLengthValidator(44)])  # "-" => don't user, user filled => don't generated

    # allowed_ips= models.ListField(child=models.CharField(max_length=18)) # in client config, accept ipv6
    allowed_ips = models.CharField(max_length=255) # blank=False --> không thể để trống --> ít nhất phải có 0.0.0.0/0
    endpoint = models.CharField(blank=True, max_length=22)  # 255.255.255.255:65000  size = 21, endpoint address of client (ip public & port of client), accept ipv6

    # extra_allowed_ips= models.ListField(child=models.CharField(min_length=9)) # in server config (alowed_ips in peer), allow empty [], accept ipv6
    extra_allowed_ips = models.CharField(blank=True, max_length=255)
    use_server_dns = models.BooleanField(default=False)
    enabled = models.BooleanField(default=False)

    additional_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # interface = models.ForeignKey(Interface, on_delete=models.PROTECT)
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return self.name