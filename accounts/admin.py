from django.contrib import admin

# Register your models here.
from .models import User,UserRole,Role

admin.site.register(UserRole)
admin.site.register(User)
admin.site.register(Role)

