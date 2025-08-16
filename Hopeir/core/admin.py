from django.contrib import admin
from .models import CustomUser, VehicleProfile
from django.contrib.auth.admin import UserAdmin

# Register your models here.
admin.site.register(VehicleProfile)

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    # Define which fields to show in the list view
    list_display = ('email', 'user_id', 'first_name', 'last_name', 'is_staff')
    # Define which fields are searchable
    search_fields = ('email', 'first_name', 'last_name')
    # Define the layout of the add/edit form
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('user_id', 'first_name', 'last_name', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    # user_id should be read-only as it comes from SuperTokens
    readonly_fields = ('user_id', 'date_joined', 'last_login')

# Register your CustomUser model with the customized admin class
admin.site.register(CustomUser, CustomUserAdmin)
