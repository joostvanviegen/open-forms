from django.contrib import admin

from solo.admin import SingletonModelAdmin

from .models import IrmaConfig


@admin.register(IrmaConfig)
class IrmaConfigAdmin(SingletonModelAdmin):
    pass
