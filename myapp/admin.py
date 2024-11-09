# myapp/admin.py
from django.contrib import admin
from .models import User, Service, ServicePackage, PackageService

admin.site.register(User)
admin.site.register(Service)

class PackageServiceInline(admin.TabularInline):
    model = PackageService
    extra = 1

@admin.register(ServicePackage)
class ServicePackageAdmin(admin.ModelAdmin):
    inlines = [PackageServiceInline]
    list_display = ['name', 'base_price', 'discount_percentage', 'is_customizable', 'created_at', 'updated_at']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  
            return list(self.readonly_fields) + ['created_at']  # Convert tuple to list before concatenation
        return list(self.readonly_fields)  