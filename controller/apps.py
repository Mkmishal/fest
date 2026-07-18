from django.apps import AppConfig

class ControllerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'controller'

def ready(self):
    import controller.signals  # replace 'yourapp' with your actual app name