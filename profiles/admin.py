from django.contrib import admin
from .models import Cv,UserInfo,CvView,CvMark
from django.contrib import admin
from django.contrib.postgres.fields import ArrayField
from django.db import models
from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import ArrayWidget, WysiwygWidget
from base.admin import BaseAdminClass

@admin.register(Cv)
class CvAdmin(BaseAdminClass):
    list_display = ('user', 'post', 'name', 'email', 'phone_number', 'status', 'created_at', 'modified_at') 
    list_filter = ('user', 'post', 'name', 'email', 'phone_number', 'status', 'created_at', 'modified_at')
    search_fields = ('user', 'post', 'name', 'email', 'phone_number', 'status', 'created_at', 'modified_at')
    list_display_links = ('user', 'post', 'name', 'email', 'phone_number', 'status', 'created_at', 'modified_at')

@admin.register(UserInfo)
class UserInfoAdmin(BaseAdminClass):
    list_display = ('user', 'fullname', 'gender', 'created_at', 'modified_at')
    list_filter = ('user', 'fullname', 'gender', 'created_at', 'modified_at')
    search_fields = ('user', 'fullname', 'gender', 'created_at', 'modified_at')
    list_display_links = ('user', 'fullname', 'gender', 'created_at', 'modified_at')

# @admin.register(CvView)
# class CvViewAdmin(BaseAdminClass):
#     list_display = ('cv', 'viewer', 'viewed_at')
#     list_filter = ('cv', 'viewer', 'viewed_at')
#     search_fields = ('cv', 'viewer', 'viewed_at')
#     list_display_links = ('cv', 'viewer', 'viewed_at')

# @admin.register(CvMark)
# class CvMarkAdmin(BaseAdminClass):
#     list_display = ('cv', 'marker', 'mark_type', 'marked_at')
#     list_filter = ('cv', 'marker', 'mark_type', 'marked_at')
#     search_fields = ('cv', 'marker', 'mark_type', 'marked_at')
#     list_display_links = ('cv', 'marker', 'mark_type', 'marked_at')



