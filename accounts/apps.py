from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # Import và áp dụng patches
        try:
            from . import patches
            patches.apply_patches()
            logger.info("Applied social auth patches successfully")
        except Exception as e:
            logger.error(f"Error applying patches: {str(e)}")
