"""URL conf module for the admin site. Imported dynamically by Include()."""

from .site import site

urlpatterns = site.get_urls()

app_name = "admin"
