from django.contrib import admin

# Register your models here.
from .models import UserAccount,UserRole,Role

admin.site.register(UserRole)
admin.site.register(UserAccount)
admin.site.register(Role)

