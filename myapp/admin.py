# myapp/admin.py
from django.contrib import admin
from .models import User, Service

admin.site.register(User)
admin.site.register(Service)  # Assuming you have a Service model as well

