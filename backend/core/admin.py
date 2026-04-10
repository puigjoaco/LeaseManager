from django.contrib import admin

from .models import PlatformSetting, Role, RoleScope, Scope, UserScopeAssignment

admin.site.register(Scope)
admin.site.register(Role)
admin.site.register(RoleScope)
admin.site.register(UserScopeAssignment)
admin.site.register(PlatformSetting)
