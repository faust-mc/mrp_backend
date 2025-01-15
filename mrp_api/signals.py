from django.db.models.signals import post_save
from .models import Modules, Submodules, ModulePermissions
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum,Count,Q,F, Exists
from decimal import Decimal
from math import floor
import datetime
import json
from django.core.serializers.json import DjangoJSONEncoder

permissions = ['add', 'view', 'update', 'delete', 'report']

@receiver(post_save)
def dynamic_permission_signal(sender, instance, created, **kwargs):


    applicable_models = ['Modules', 'Submodules']  # Add your model names here
    model_name = sender.__name__

    if model_name in applicable_models and created:
        # Use ContentType to associate permissions with the correct model
        content_type = ContentType.objects.get_for_model(sender)
        print("l----")
        print(content_type)
        print(instance.slug)
        print("i-----")

        for permission in permissions:
            name = f'Can {permission} {instance.slug} {model_name.lower()}'
            codename = f'{permission}_{instance.slug}'  # Use instance.id or another unique attribute
            # Save permission to the database
            data = ModulePermissions(name=name, codename=codename, content_type_id=instance.id)
            data.save()