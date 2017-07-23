# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from core.models import UserRepo, Issue, IssueLabel, Region, RegionAdmin
from django.contrib.auth.models import *


class RegionAdminInline(admin.StackedInline):
    """
    Define an inline admin descriptor for RegionAdmin model
    which acts a bit like a singleton.
    """
    
    model = RegionAdmin
    can_delete = False
    verbose_name_plural = 'region_admin'

class UserAdmin(BaseUserAdmin):
    """Define a new User admin."""
    inlines = (RegionAdminInline, )

admin.site.unregister(Group)
# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

admin.site.register(UserRepo)
admin.site.register(Region)
