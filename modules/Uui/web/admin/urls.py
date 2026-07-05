"""URL conf module for the admin site. Imported dynamically by Include()."""
from ..router import path
from . import views
from .site import site


urlpatterns = site.get_urls()

app_name = 'admin'
