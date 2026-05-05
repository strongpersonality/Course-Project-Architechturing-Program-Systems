from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.admin_dashboard, name='admin_dashboard'),
    path('login/', auth_views.LoginView.as_view(template_name='admin_panel/login.html'), name='admin_login'),
    path('logout/', auth_views.LogoutView.as_view(), name='admin_logout'),
    path('add-booking/step1/', views.add_booking_step1, name='add_booking_step1'),
    path('add-booking/step2/', views.add_booking_step2, name='add_booking_step2'),
    path('add-booking/final/<int:room_id>/', views.add_booking_final, name='add_booking_final'),
    path('add-room/', views.add_room, name='add_room'),
    path('update-room-status/<int:room_id>/', views.update_room_status, name='update_room_status'),
    path('mark-notification/<int:notif_id>/', views.mark_notification_read, name='mark_notification'),
    path('cancel-booking/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('confirm-booking/<int:booking_id>/', views.confirm_booking_admin, name='confirm_booking_admin'),
    path('checkin-booking/<int:booking_id>/', views.checkin_booking, name='checkin_booking'),
    path('checkout-booking/<int:booking_id>/', views.checkout_booking, name='checkout_booking'),
    path('delete-room/<int:room_id>/', views.delete_room, name='delete_room'),
]