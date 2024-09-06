from django.contrib.auth.models import AbstractUser

# Create your models here.
class User(AbstractUser):
    # fields default: ['logentry', 'id', 'password', 'last_login', 'is_superuser', 'username', 
    #              'first_name', 'last_name', 'email', 'is_staff', 'is_active', 'date_joined', 'groups', 'user_permissions']
    # is_superuser = None
    last_login = None
    first_name = None
    last_name = None
    groups = None
    user_permissions = None
    
    def __str__(self):
        return self.username