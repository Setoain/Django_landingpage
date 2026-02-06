from django.contrib import admin
from .models import Email


@admin.register(Email)
class EmailAdmin(admin.ModelAdmin):
    list_display = ['email', 'id']
    search_fields = ['email']
    ordering = ['id']