from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path('', views.booking_search, name='booking_search'),
    path('search/', views.search_rooms, name='search_rooms'),
    path('book/<int:room_id>/', views.booking_details, name='booking_details'),
    path('send-code/', views.send_confirmation_code, name='send_confirmation_code'),
    path('confirm/', views.confirm_booking, name='confirm_booking'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)