from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from .vpnconnection import VpnConnection 


class VpnConnectionStatus(models.Model):
    curr_endpoint = models.CharField(max_length=40)
    latest_handshake = models.BigIntegerField(default=0)
    receive = models.BigIntegerField(default=0)
    transmit = models.BigIntegerField(default=0)
    peer = models.ForeignKey(VpnConnection, null=True, on_delete=models.SET_NULL)
    type = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(3)])  # 0 -> normal, 1 -> change endpoint, 2 + peer NULL --> reset wg
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at', 'id']