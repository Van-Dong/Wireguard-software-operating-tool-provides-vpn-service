from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class GlobalSetting(models.Model):
    endpoint_address = models.CharField(max_length=15) # ip public or ip server (not ip interface wireguard)
    dns_servers = models.CharField(blank=True, max_length=255) # 255.255.255.255 has size = 15
    mtu = models.IntegerField(null=True, default=None, validators=[MinValueValidator(18), MaxValueValidator(65535)])  # requried = False, if don't use, set = 0 (null)
    persistent_keepalive = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(65535)]) # requried = False, if don't use, set = 0 (null)
    table = models.CharField(blank=True, max_length=10) # requried = False, if don't use, set = "" 
    firewall_mark = models.CharField(blank=True, max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name_interface