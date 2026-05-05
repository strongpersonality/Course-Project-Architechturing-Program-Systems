from django.shortcuts import render
from django.utils import timezone
from django.conf import settings
from django.db.models import Q
from .models import *
def booking_search(request):
    """Шаг 1: Поиск номеров"""
    context = {
        'show_steps': True,
        'steps': [
            (1, 'Поиск номера'),
            (2, 'Выбор номера'),
            (3, 'Оформление'),
            (4, 'Подтверждение'),
        ],
        'current_step': 1,
        'today': timezone.now().date(),
        'recaptcha_public_key': settings.RECAPTCHA_PUBLIC_KEY,
    }
    return render(request, 'booking/step1_search.html', context)


def search_rooms(request):
    """Шаг 2: Поиск и показ доступных номеров"""
    check_in = request.GET.get('check_in')
    check_out = request.GET.get('check_out')
    guests = int(request.GET.get('guests', 1))
    print(f"=== search_rooms ===")
    print(f"check_in: {check_in}")
    print(f"check_out: {check_out}")
    print(f"guests: {guests}")
    if check_in >= check_out:
        messages.error(request, 'Дата выезда должна быть позже даты заезда')
        return redirect('booking_search')
    # Получаем все номера, которые подходят по вместимости
    rooms = Room.objects.filter(
        room_type__max_occupancy__gte=guests
    ).select_related('room_type')

    # Исключаем номера, которые уже забронированы на эти даты
    if check_in and check_out:
        booked_room_ids = Booking.objects.filter(
            Q(check_in_date__lt=check_out, check_out_date__gt=check_in),
            status__in=['confirmed', 'checked_in']
        ).values_list('room_id', flat=True)

        rooms = rooms.exclude(room_id__in=booked_room_ids)

    context = {
        'show_steps': True,
        'steps': [
            (1, 'Поиск номера'),
            (2, 'Выбор номера'),
            (3, 'Оформление'),
            (4, 'Подтверждение'),
        ],
        'current_step': 2,
        'rooms': rooms,
        'check_in': check_in,
        'check_out': check_out,
        'guests': guests,
    }
    return render(request, 'booking/step2_rooms.html', context)


def booking_details(request, room_id):
    """Шаг 3: Форма для ввода данных гостя"""
    check_in = request.GET.get('check_in')
    check_out = request.GET.get('check_out')
    guests = int(request.GET.get('guests', 1))
    print(f"=== booking_details ===")
    print(f"check_in: {check_in}")
    print(f"check_out: {check_out}")
    print(f"guests: {guests}")
    from .models import Room
    from datetime import datetime

    room = Room.objects.select_related('room_type').get(room_id=room_id)

    check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
    check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
    nights = (check_out_date - check_in_date).days
    total_price = room.room_type.base_price * nights

    context = {
        'show_steps': True,
        'steps': [  # <-- ВАЖНО: список кортежей (номер, название)
            (1, 'Поиск номера'),
            (2, 'Выбор номера'),
            (3, 'Оформление'),
            (4, 'Подтверждение'),
        ],
        'current_step': 3,
        'room': room,
        'check_in': check_in,
        'check_out': check_out,
        'guests': guests,
        'nights': nights,
        'total_price': total_price,
    }
    return render(request, 'booking/step3_booking.html', context)
import random
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings


def send_confirmation_code(request):
    """Отправка кода подтверждения или создание уведомления для админа"""
    if request.method == 'POST':
        room_id = request.POST.get('room_id')
        check_in = request.POST.get('check_in')
        check_out = request.POST.get('check_out')
        print(f"=== send_conf ===")
        print(f"check_in: {check_in}")
        print(f"check_out: {check_out}")
        guests = request.POST.get('guests', 1)
        total_price = request.POST.get('total_price')

        last_name = request.POST.get('last_name')
        first_name = request.POST.get('first_name')
        patronymic = request.POST.get('patronymic', '')
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone_number', '').strip()
        special_requests = request.POST.get('special_requests', '')

        # 1. Проверка: хотя бы email или телефон
        if not email and not phone:
            messages.error(request, 'Укажите хотя бы email или номер телефона для связи.')
            return render_booking_form(request, room_id, check_in, check_out, guests, total_price,
                                       last_name, first_name, patronymic, email, phone, special_requests)

        # 2. Если email указан – отправляем код подтверждения
        if email:
            import random
            confirmation_code = str(random.randint(100000, 999999))
            request.session['booking_data'] = {
                'room_id': room_id,
                'check_in': check_in,
                'check_out': check_out,
                'guests': guests,
                'total_price': total_price,
                'last_name': last_name,
                'first_name': first_name,
                'patronymic': patronymic,
                'email': email,
                'phone': phone,
                'special_requests': special_requests,
                'confirmation_code': confirmation_code,
            }
            # Отправка письма
            try:
                from django.core.mail import send_mail
                from django.conf import settings
                send_mail(
                    'Код подтверждения бронирования',
                    f'Ваш код подтверждения: {confirmation_code}\n\nНикому не сообщайте этот код.',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Ошибка отправки письма: {e}")
            # Переход на страницу ввода кода
            return render(request, 'booking/email_checkform.html', {
                'show_steps': True,
                'steps': [(1, 'Поиск'), (2, 'Выбор'), (3, 'Оформление'), (4, 'Подтверждение')],
                'current_step': 3,
                'email': email,
                'attempts': 0,
            })

        # 3. Если email не указан, но телефон указан – создаём бронь и уведомление для админа
        if not email and phone:
            from .models import AdminNotification, Room, Guest, Booking
            from django.utils import timezone
            from datetime import datetime

            # Проверяем, не было ли уже такого уведомления за последние 10 минут
            time_threshold = timezone.now() - timezone.timedelta(minutes=10)
            existing = AdminNotification.objects.filter(
                guest_phone=phone,
                check_in=check_in,
                check_out=check_out,
                is_read=False,
                created_at__gte=time_threshold
            ).exists()

            if not existing:
                room = Room.objects.get(room_id=room_id)

                # СОЗДАЁМ ГОСТЯ (если его ещё нет)
                guest, created = Guest.objects.get_or_create(
                    phone_number=phone,
                    defaults={
                        'last_name': last_name,
                        'first_name': first_name,
                        'patronymic': patronymic,
                        'email': email or '',
                    }
                )

                # Если гость уже существовал, обновляем данные
                if not created:
                    guest.last_name = last_name
                    guest.first_name = first_name
                    guest.patronymic = patronymic
                    guest.save()

                # СОЗДАЁМ БРОНИРОВАНИЕ СО СТАТУСОМ "NEW"
                check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
                check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
                nights = (check_out_date - check_in_date).days
                total_price_calc = room.room_type.base_price * nights

                booking = Booking.objects.create(
                    guest=guest,
                    room=room,
                    check_in_date=check_in,
                    check_out_date=check_out,
                    guests_count=guests,
                    total_price=total_price_calc,
                    status='new',  # <-- СТАТУС "НОВОЕ"
                    special_requests=special_requests
                )

                # Создаём уведомление для админа
                AdminNotification.objects.create(
                    notification_type='phone_booking',
                    message=f'Клиент {last_name} {first_name} оставил заявку без email. Требуется звонок.',
                    guest_name=f'{last_name} {first_name} {patronymic}',
                    guest_phone=phone,
                    check_in=check_in,
                    check_out=check_out,
                    guests=guests,
                    booking_id=booking.booking_id  # связываем с бронированием
                )

                # Отправляем письмо администратору
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings
                    send_mail(
                        'Требуется звонок клиенту',
                        f'Клиент: {last_name} {first_name}\nТелефон: {phone}\nДаты: {check_in} - {check_out}\nНомер: {room.room_number}\n\nСсылка на бронь: /admin-panel/?tab=bookings',
                        settings.DEFAULT_FROM_EMAIL,
                        [settings.ADMIN_EMAIL],
                        fail_silently=False,
                    )
                except:
                    pass

                messages.success(request,
                                 f'Заявка на бронирование #{booking.booking_id} отправлена администратору. Он свяжется с вами.')
            else:
                messages.info(request, 'Вы уже оставляли заявку. Администратор свяжется с вами в ближайшее время.')

            return redirect('booking_search')
def confirm_booking(request):
    """Подтверждение бронирования по коду"""
    if request.method == 'POST':
        entered_code = request.POST.get('confirmation_code')
        booking_data = request.session.get('booking_data')

        if not booking_data:
            messages.error(request, 'Сессия истекла. Начните бронирование заново.')
            return redirect('booking_search')
        attempts = booking_data.get('attempts', 0)
        # Проверяем код
        if entered_code == booking_data.get('confirmation_code'):
            # Код верный - создаём бронь в БД
            from .models import Guest, Room, Booking

            # Создаём гостя
            guest = Guest.objects.create(
                last_name=booking_data['last_name'],
                first_name=booking_data['first_name'],
                patronymic=booking_data.get('patronymic', ''),
                email=booking_data['email'],
                phone_number=booking_data.get('phone', '')
            )

            # Получаем номер
            room = Room.objects.get(room_id=booking_data['room_id'])

            # Создаём бронь
            booking = Booking.objects.create(
                guest=guest,
                room=room,
                check_in_date=booking_data['check_in'],
                check_out_date=booking_data['check_out'],
                guests_count=booking_data['guests'],
                total_price=int(float(booking_data['total_price'])),
                status='confirmed',
                special_requests=booking_data.get('special_requests', '')
            )
            room.status = 'occupied'
            room.save()
            subject = f'Подтверждение бронирования #{booking.booking_id}'
            message = f"""
            Здравствуйте, {guest.first_name} {guest.last_name}!

            Ваше бронирование в отеле "Черное и белое" подтверждено.

            Детали бронирования:
            ─────────────────────
            Номер бронирования: #{booking.booking_id}
            Номер: {room.room_number} ({room.room_type.type_name})
            Дата заезда: {booking.check_in_date}
            Дата выезда: {booking.check_out_date}
            Количество гостей: {booking.guests_count}
            Стоимость: {booking.total_price} руб.

            Дополнительные пожелания:
            {booking.special_requests or 'Нет'}

            Если у вас возникли вопросы, свяжитесь с нами.

            С уважением,
            Отель "Черное и белое"
                            """

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [guest.email],
                fail_silently=False,
            )
            # Очищаем сессию
            del request.session['booking_data']
            # Переходим на страницу успеха
            return render(request, 'booking/completed_transaction.html', {
                'show_steps': True,
                'steps': [
                    (1, 'Поиск номера'),
                    (2, 'Выбор номера'),
                    (3, 'Оформление'),
                    (4, 'Подтверждение'),
                ],
                'current_step': 4,
                'booking': booking,
            })
        else:
            # Неверный код - увеличиваем счётчик
            attempts += 1
            booking_data['attempts'] = attempts
            request.session['booking_data'] = booking_data

            # Проверяем количество попыток
            if attempts >= 3:
                # 3 неудачные попытки - очищаем сессию и отправляем на начало
                del request.session['booking_data']
                messages.error(request,
                               'Превышено количество попыток ввода кода. Пожалуйста, начните бронирование заново.')
                return redirect('booking_search')

            # Определяем сообщение в зависимости от попытки
            if attempts == 2:
                error_msg = 'Неверный код. Осталась последняя попытка!'
            else:
                error_msg = f'Неверный код. Осталось {3 - attempts} попытки.'

            messages.error(request, error_msg)

            return render(request, 'booking/email_checkform.html', {
                'show_steps': True,
                'steps': [
                    (1, 'Поиск номера'),
                    (2, 'Выбор номера'),
                    (3, 'Оформление'),
                    (4, 'Подтверждение'),
                ],
                'current_step': 3,
                'email': booking_data.get('email'),
                'error': error_msg,
                'attempts': attempts,  # передаём количество попыток в шаблон
            })

        return redirect('booking_search')
def render_booking_form(request, room_id, check_in, check_out, guests, total_price,
                        last_name, first_name, patronymic, email, phone, special_requests):
    """Возвращает страницу с формой бронирования, заполненную переданными данными"""
    from .models import Room
    from datetime import datetime
    room = Room.objects.select_related('room_type').get(room_id=room_id)
    check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
    check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
    nights = (check_out_date - check_in_date).days
    if not total_price:
        total_price = room.room_type.base_price * nights
    context = {
        'show_steps': True,
        'steps': [(1, 'Поиск номера'), (2, 'Выбор номера'), (3, 'Оформление'), (4, 'Подтверждение')],
        'current_step': 3,
        'room': room,
        'check_in': check_in,
        'check_out': check_out,
        'guests': guests,
        'nights': nights,
        'total_price': total_price,
        'last_name': last_name,
        'first_name': first_name,
        'patronymic': patronymic,
        'email': email,
        'phone': phone,
        'special_requests': special_requests,
    }
    return render(request, 'booking/step3_booking.html', context)
    return render(request, 'booking/step3_booking.html', context)