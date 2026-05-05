from django.contrib import admin
from .models import Guest, RoomType, Room, Booking

admin.site.register(Guest)
admin.site.register(RoomType)
admin.site.register(Room)
admin.site.register(Booking)