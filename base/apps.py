from django.apps import AppConfig


class BaseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'base'

    def ready(self):
        # Python 3.14 + Django 5.1 compatibility patch for Context.__copy__
        from django.template.context import BaseContext

        def patched_base_context_copy(self):
            duplicate = self.__class__.__new__(self.__class__)
            duplicate.__dict__.update(self.__dict__)
            duplicate.dicts = self.dicts[:]
            return duplicate

        BaseContext.__copy__ = patched_base_context_copy
