from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from accounts import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls',namespace='accounts')),
    path('home/', views.home, name='home'),  # Add this line for the root URL
    # If you want /accounts/ to redirect to home:
    # path('accounts/', RedirectView.as_view(url='/', permanent=True)),
    path('jobs/', include('jobs.urls', namespace='jobs')),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)