from django.db.models.signals import post_save
from .models import Modules, ModulePermissions
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum,Count,Q,F, Exists
from decimal import Decimal
from math import floor
import datetime
import json
from django.core.serializers.json import DjangoJSONEncoder

permissions = ['add', 'view', 'edit', 'delete', 'report']

@receiver(post_save)
def dynamic_permission_signal(sender, instance, created, **kwargs):

    applicable_models = ['Modules']
    model_name = sender.__name__

    if model_name in applicable_models and created:
        #use ContentType to associate permissions with the correct model
        content_type = ContentType.objects.get_for_model(sender)

        for permission in permissions:
            name = f'Can {permission} {instance.slug} {model_name.lower()}'
            codename = f'{permission}_{instance.slug}'
            data = ModulePermissions(name=name, codename=codename)
            data.save()