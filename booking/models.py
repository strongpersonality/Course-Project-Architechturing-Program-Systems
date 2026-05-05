from django.db import models


class Guest(models.Model):
    guest_id = models.AutoField(primary_key=True)
    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    patronymic = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.last_name} {self.first_name}"

    class Meta:
        db_table = 'guest'


class RoomType(models.Model):
    room_type_id = models.AutoField(primary_key=True)
    type_name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    max_occupancy = models.IntegerField()
    image = models.ImageField(upload_to='room_images/', null=True, blank=True, verbose_name="Изображение номера")

    def __str__(self):
        return self.type_name

    class Meta:
        db_table = 'room_type'
class Room(models.Model):
    ROOM_STATUS = [
        ('available', 'Свободен'),
        ('occupied', 'Занят'),
        ('cleaning', 'Уборка'),
        ('maintenance', 'Обслуживание'),
    ]

    room_id = models.AutoField(primary_key=True)
    room_number = models.CharField(max_length=10, unique=True)
    floor = models.IntegerField()
    status = models.CharField(max_length=20, choices=ROOM_STATUS, default='available')
    room_type = models.ForeignKey(RoomType, on_delete=models.RESTRICT, db_column='room_type_id')

    def __str__(self):
        return f"Номер {self.room_number}"

    class Meta:
        db_table = 'room'


class Booking(models.Model):
    BOOKING_STATUS = [
        ('new', 'Новое'),
        ('confirmed', 'Подтверждено'),
        ('checked_in', 'Заселился'),
        ('checked_out', 'Выселился'),
        ('cancelled', 'Отменено'),
    ]

    booking_id = models.AutoField(primary_key=True)
    check_in_date = models.DateField()
    check_out_date = models.DateField()
    guests_count = models.IntegerField()
    status = models.CharField(max_length=20, choices=BOOKING_STATUS, default='new')
    special_requests = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    guest = models.ForeignKey(Guest, on_delete=models.PROTECT, db_column='guest_id')
    room = models.ForeignKey(Room, on_delete=models.PROTECT, db_column='room_id')
    total_price = models.IntegerField()

    def __str__(self):
        return f"Бронь #{self.booking_id} - {self.guest}"

    class Meta:
        db_table = 'booking'


class AdminNotification(models.Model):
    NOTIFICATION_TYPES = [
        ('phone_booking', 'Требуется звонок клиенту'),
        ('cancellation', 'Требуется уведомить об отмене'),
        ('system', 'Системное уведомление'),
    ]

    id = models.AutoField(primary_key=True)
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='phone_booking')
    message = models.TextField()
    guest_name = models.CharField(max_length=200, blank=True)
    guest_phone = models.CharField(max_length=20, blank=True)
    guest_email = models.EmailField(blank=True)
    check_in = models.DateField(null=True, blank=True)
    check_out = models.DateField(null=True, blank=True)
    guests = models.IntegerField(default=1)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    booking_id = models.IntegerField(null=True, blank=True, verbose_name="ID бронирования")
    class Meta:
        db_table = 'admin_notification'
        ordering = ['-created_at']

    def __str__(self):
        return f"Уведомление #{self.id}: {self.message[:50]}"