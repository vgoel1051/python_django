"""
    Admin panel registration
"""

from django.contrib import admin
from .models import EbayItem

# Register your models here.
admin.site.register(EbayItem)
