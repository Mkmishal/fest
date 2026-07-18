# signals.py
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from .models import OnlineProfile
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.core.serializers import serialize
import json



@receiver(post_save, sender=User)
def create_online_profile(sender, instance, created, **kwargs):
    """Ensure every user has an OnlineProfile."""
    if created:
        OnlineProfile.objects.create(user=instance)


@receiver(user_logged_in)
def user_logged_in_handler(sender, request, user, **kwargs):
    """Mark user as online when they log in."""
    profile, created = OnlineProfile.objects.get_or_create(user=user)
    profile.is_online = True
    profile.save()


@receiver(user_logged_out)
def user_logged_out_handler(sender, request, user, **kwargs):
    """Mark user as offline when they log out."""
    try:
        profile = OnlineProfile.objects.get(user=user)
        profile.is_online = False
        profile.save()
    except OnlineProfile.DoesNotExist:
        pass