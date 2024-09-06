from django.db import models
from django.core.validators import MinLengthValidator, MinValueValidator, MaxValueValidator

class Interface(models.Model):
    name = models.CharField(max_length=255, unique=True)
    addresses = models.CharField(max_length=255)
    listen_port = models.IntegerField(validators=[MinValueValidator(1024), MaxValueValidator(65535)], unique=True)
    enabled = models.BooleanField(default=False)
    pre_up = models.CharField(blank=True, max_length=200)
    post_up = models.CharField(blank=True, max_length=200) # requried = False, if don't use, set = ""
    pre_down = models.CharField(blank=True, max_length=200) # requried = False, if don't use, set = ""
    post_down = models.CharField(blank=True, max_length=200) # requried = False, if don't use, set = ""
    private_key = models.CharField(max_length=44, validators=[MinLengthValidator(44)])
    public_key = models.CharField(max_length=44, validators=[MinLengthValidator(44)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return 'Port ' + str(self.listen_port)