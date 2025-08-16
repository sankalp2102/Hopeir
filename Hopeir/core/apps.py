from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        # This method is called once Django is fully initialized
        from . import supertokens  # Import your new file
        supertokens.init_supertokens() # Run the initialization
