from django.apps import AppConfig

class MrpApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mrp_api'

    def ready(self):
        import mrp_api.signals  # Existing signal import
        from mrp_api.data_processor import scheduler  # Import the scheduler

        if not scheduler.running:  # Prevent multiple instances during Django reloads
            scheduler.start()
