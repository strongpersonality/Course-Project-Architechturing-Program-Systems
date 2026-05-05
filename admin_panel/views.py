from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count, Sum
import calendar
from datetime import datetime, timedelta
from django.db.models import Count, Sum, Avg
# Импортируем модели из booking
from booking.models import Guest, Booking, Room, RoomType


@login_required
def admin_dashboard(request):
    """Главная страница админ-панели"""
    tab = request.GET.get('tab', 'dashboard')

    # Получаем месяц и год из GET-параметров или используем текущие
    year_param = request.GET.get('year', '')
    month_param = request.GET.get('month', '')

    if year_param and month_param:
        try:
            year = int(year_param)
            month = int(month_param)
        except ValueError:
            year = timezone.now().year
            month = timezone.now().month
    else:
        year = timezone.now().year
        month = timezone.now().month

    context = {
        'active_tab': tab,
        'current_year': year,
        'current_month': month,
        'month_name': calendar.month_name[month],
    }

    # Загружаем данные в зависимости от вкладки
    if tab == 'bookings':

        # Базовый запрос
        bookings = Booking.objects.all().select_related('guest', 'room__room_type').order_by('-created_at')

        # Фильтрация по номеру
        room_filter = request.GET.get('room_filter')
        if room_filter and room_filter != 'all':
            bookings = bookings.filter(room_id=room_filter)

        # Фильтрация по статусу
        status_filter = request.GET.get('status_filter')
        if status_filter and status_filter != 'all':
            bookings = bookings.filter(status=status_filter)

        # Фильтрация по дате
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        if date_from:
            bookings = bookings.filter(created_at__date__gte=date_from)
        if date_to:
            bookings = bookings.filter(created_at__date__lte=date_to)

        # Получаем список всех номеров для выпадающего списка
        all_rooms = Room.objects.all().order_by('room_number')

        context['bookings'] = bookings
        context['today'] = timezone.now().date()
        context['all_rooms'] = all_rooms
        context['room_filter'] = room_filter
        context['status_filter'] = status_filter
        context['date_from'] = date_from
        context['date_to'] = date_to

    elif tab == 'rooms':
        rooms = Room.objects.all().select_related('room_type').order_by('room_number')
        room_types = RoomType.objects.all()

        context['rooms'] = rooms
        context['room_types'] = room_types
        context['status_choices'] = Room.ROOM_STATUS




    elif tab == 'reports':


        # Получаем даты из GET параметров или ставим текущий месяц

        today = timezone.now().date()

        start_date = request.GET.get('start_date', today.replace(day=1).strftime('%Y-%m-%d'))

        end_date = request.GET.get('end_date', today.strftime('%Y-%m-%d'))

        period = request.GET.get('period', 'month')

        selected_room_id = request.GET.get('room_id', 'all')

        # Преобразуем строки в даты

        try:

            start = datetime.strptime(start_date, '%Y-%m-%d').date()

            end = datetime.strptime(end_date, '%Y-%m-%d').date()

        except:

            start = today.replace(day=1)

            end = today

        # Все номера для выпадающего списка

        all_rooms = Room.objects.all().select_related('room_type').order_by('room_number')

        # Базовая выборка бронирований

        bookings_query = Booking.objects.filter(

            check_in_date__lte=end,  # заезд не позже конца периода

            check_out_date__gte=start,  # выезд не раньше начала периода

            status__in=['confirmed', 'checked_in', 'checked_out']

        )
        # Фильтруем по номеру если выбран конкретный

        if selected_room_id and selected_room_id != 'all':
            bookings_query = bookings_query.filter(room_id=selected_room_id)

        # 1. Общее количество бронирований (уникальных)

        total_bookings = bookings_query.count()
        # 2. Заполняемость

        if selected_room_id and selected_room_id != 'all':

            # Для конкретного номера

            days_in_period = (end - start).days

            occupied_days = 0

            current = start

            while current < end:

                is_occupied = Booking.objects.filter(

                    room_id=selected_room_id,

                    check_in_date__lte=current,

                    check_out_date__gte=current,

                    status__in=['confirmed', 'checked_in']

                ).exists()

                if is_occupied:
                    occupied_days += 1

                current += timedelta(days=1)

            occupancy = (occupied_days / days_in_period * 100) if days_in_period > 0 else 0


        else:

            # Для всех номеров

            total_rooms = Room.objects.count()

            if total_rooms > 0:

                days = (end - start).days

                total_room_days = total_rooms * days

                occupied_room_days = 0

                current = start

                while current < end:
                    occupied = Booking.objects.filter(

                        check_in_date__lte=current,

                        check_out_date__gte=current,

                        status__in=['confirmed', 'checked_in']

                    ).count()

                    occupied_room_days += occupied

                    current += timedelta(days=1)

                occupancy = (occupied_room_days / total_room_days * 100) if total_room_days > 0 else 0

            else:

                occupancy = 0

        # 3. Общий доход

        total_income = 0

        for booking in bookings_query:
            # Определяем сколько дней из брони попадают в выбранный период

            booking_start = max(booking.check_in_date, start)

            booking_end = min(booking.check_out_date, end)

            days_in_period = (booking_end - booking_start).days

            # Цена за ночь

            price_per_night = booking.room.room_type.base_price

            # Добавляем пропорциональный доход

            total_income += price_per_night * days_in_period

        context['total_bookings'] = total_bookings

        context['occupancy'] = round(occupancy, 1)

        context['total_income'] = round(total_income, 2)

        context['start_date'] = start.strftime('%Y-%m-%d')

        context['end_date'] = end.strftime('%Y-%m-%d')

        context['period'] = period

        context['all_rooms'] = all_rooms

        context['selected_room_id'] = selected_room_id
    elif tab == 'calendar':

        # Получаем все номера для выпадающего списка

        all_rooms = Room.objects.all().select_related('room_type').order_by('room_number')

        # Получаем выбранный номер из GET параметров

        selected_room_id = request.GET.get('room_id')

        show_calendar = False

        bookings_data = {}

        if selected_room_id and selected_room_id.isdigit():

            selected_room_id = int(selected_room_id)

            show_calendar = True

            # Получаем все бронирования для этого номера на выбранный месяц

            month_start = datetime(year, month, 1).date()

            if month == 12:

                month_end = datetime(year + 1, 1, 1).date() - timedelta(days=1)

            else:

                month_end = datetime(year, month + 1, 1).date() - timedelta(days=1)

            bookings = Booking.objects.filter(

                room_id=selected_room_id,

                check_in_date__lte=month_end,

                check_out_date__gte=month_start,

                status__in=['confirmed', 'checked_in']

            )

            # Отмечаем занятые дни

            for booking in bookings:

                start = max(booking.check_in_date, month_start)

                end = min(booking.check_out_date, month_end)

                current = start

                while current <= end:
                    bookings_data[current.day] = True

                    current += timedelta(days=1)

        # Создаем календарную сетку

        cal = calendar.monthcalendar(year, month)

        context['all_rooms'] = all_rooms

        context['selected_room_id'] = selected_room_id

        context['show_calendar'] = show_calendar

        context['calendar'] = cal

        context['bookings_data'] = bookings_data

        context['month_name'] = calendar.month_name[month]

        context['year'] = year
    elif tab == 'dashboard':
        from booking.models import AdminNotification
        unread_notifications = AdminNotification.objects.filter(is_read=False)[:10]
        context['unread_notifications'] = unread_notifications
        # Статистика для дашборда
        today = timezone.now().date()
        month_start = today.replace(day=1)

        context['new_bookings_count'] = Booking.objects.filter(created_at__date=today).count()
        context['guests_today'] = Booking.objects.filter(
            check_in_date=today,
            status__in=['confirmed', 'checked_in']
        ).count()

        context['available_rooms'] = Room.objects.filter(status='available').count()

        month_income = Booking.objects.filter(
            created_at__date__gte=month_start,
            status='confirmed'
        ).aggregate(Sum('total_price'))['total_price__sum'] or 0
        context['month_income'] = month_income

        recent_bookings = Booking.objects.all().order_by('-created_at')[:5]
        context['recent_activity'] = []
        for booking in recent_bookings:
            context['recent_activity'].append({
                'text': f'Новое бронирование #{booking.booking_id}',
                'time': booking.created_at,
                'guest': f'{booking.guest.last_name} {booking.guest.first_name}'
            })

    return render(request, 'admin_panel/dash.html', context)

@login_required
def mark_notification_read(request, notif_id):
    """Отметить уведомление как прочитанное"""
    from booking.models import AdminNotification
    try:
        notif = AdminNotification.objects.get(id=notif_id)
        notif.is_read = True
        notif.save()
    except:
        pass
    return redirect('/admin-panel/?tab=dashboard')
@login_required
def add_booking_step1(request):
    """Шаг 1: выбор дат для бронирования"""
    if request.method == 'POST':
        check_in = request.POST.get('check_in')
        check_out = request.POST.get('check_out')
        guests = request.POST.get('guests', 1)

        # Проверяем даты
        try:
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()

            if check_in_date >= check_out_date:
                messages.error(request, 'Дата выезда должна быть позже даты заезда')
                return redirect('/admin-panel/?tab=bookings')

            if check_in_date < datetime.now().date():
                messages.error(request, 'Дата заезда не может быть в прошлом')
                return redirect('/admin-panel/?tab=bookings')

        except:
            messages.error(request, 'Некорректный формат дат')
            return redirect('/admin-panel/?tab=bookings')

        # Сохраняем даты в сессии
        request.session['booking_dates'] = {
            'check_in': check_in,
            'check_out': check_out,
            'guests': guests
        }

        # Переходим к выбору номера
        return redirect('/admin-panel/add-booking/step2/')

    return redirect('/admin-panel/?tab=bookings')


@login_required
def add_booking_step2(request):
    """Шаг 2: выбор доступного номера"""
    dates = request.session.get('booking_dates')

    if not dates:
        messages.error(request, 'Сначала выберите даты')
        return redirect('/admin-panel/?tab=bookings')

    check_in = dates['check_in']
    check_out = dates['check_out']
    guests = int(dates['guests'])

    # Считаем количество ночей
    check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
    check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
    nights = (check_out_date - check_in_date).days

    # Все номера, подходящие по вместимости
    available_rooms = Room.objects.filter(
        room_type__max_occupancy__gte=guests
    ).select_related('room_type')

    # Исключаем занятые на эти даты
    booked_room_ids = Booking.objects.filter(
        status__in=['confirmed', 'checked_in'],
        check_in_date__lt=check_out,
        check_out_date__gt=check_in
    ).values_list('room_id', flat=True)

    available_rooms = available_rooms.exclude(room_id__in=booked_room_ids)

    # Для каждого номера считаем итоговую цену
    for room in available_rooms:
        room.total_price = room.room_type.base_price * nights

    context = {
        'rooms': available_rooms,
        'check_in': check_in,
        'check_out': check_out,
        'guests': guests,
        'nights': nights,
    }

    return render(request, 'admin_panel/select_room.html', context)


@login_required
def add_booking_final(request, room_id):
    """Шаг 3: создание брони с данными гостя"""
    dates = request.session.get('booking_dates')

    if not dates:
        messages.error(request, 'Сессия истекла, начните заново')
        return redirect('/admin-panel/?tab=bookings')

    if request.method == 'POST':
        try:
            # Получаем данные из формы
            last_name = request.POST.get('last_name')
            first_name = request.POST.get('first_name')
            patronymic = request.POST.get('patronymic', '')
            phone = request.POST.get('phone')
            email = request.POST.get('email')

            check_in = dates['check_in']
            check_out = dates['check_out']
            guests = int(dates['guests'])

            # ПОИСК СУЩЕСТВУЮЩЕГО ГОСТЯ
            guest = None
            guest_found = False

            # Ищем по телефону (приоритет)
            if phone:
                guest = Guest.objects.filter(phone_number=phone).first()
                if guest:
                    guest_found = True
                    # Проверяем, совпадают ли ФИО
                    if (guest.last_name != last_name or
                            guest.first_name != first_name or
                            guest.patronymic != patronymic):
                        messages.warning(
                            request,
                            f'Найден гость с телефоном {phone}: {guest.last_name} {guest.first_name}. '
                            f'Данные в форме отличаются. Бронь будет создана для найденного гостя.'
                        )

            # Если не нашли по телефону, ищем по email
            if not guest and email:
                guest = Guest.objects.filter(email=email).first()
                if guest:
                    guest_found = True
                    if (guest.last_name != last_name or
                            guest.first_name != first_name or
                            guest.patronymic != patronymic):
                        messages.warning(
                            request,
                            f'Найден гость с email {email}: {guest.last_name} {guest.first_name}. '
                            f'Данные в форме отличаются. Бронь будет создана для найденного гостя.'
                        )

            # Если гость не найден, создаём нового
            if not guest:
                guest = Guest.objects.create(
                    last_name=last_name,
                    first_name=first_name,
                    patronymic=patronymic,
                    phone_number=phone,
                    email=email
                )
                messages.info(request, f'Создана новая запись гостя: {last_name} {first_name}')
            else:
                # Обновляем контактные данные существующего гостя, если они изменились
                updated = False
                if email and guest.email != email:
                    guest.email = email
                    updated = True
                if phone and guest.phone_number != phone:
                    guest.phone_number = phone
                    updated = True

                if updated:
                    guest.save()
                    messages.info(request, 'Контактные данные гостя обновлены')

            # Получаем номер
            room = Room.objects.get(room_id=room_id)

            # Считаем стоимость
            check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
            check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
            nights = (check_out_date - check_in_date).days
            total_price = room.room_type.base_price * nights

            # Создаём бронь
            booking = Booking.objects.create(
                guest=guest,
                room=room,
                check_in_date=check_in,
                check_out_date=check_out,
                guests_count=guests,
                total_price=total_price,
                status='confirmed',
                special_requests=request.POST.get('special_requests', '')
            )

            # Меняем статус номера
            room.status = 'occupied'
            room.save()

            # Очищаем сессию
            del request.session['booking_dates']

            # Итоговое сообщение
            if guest_found:
                messages.success(
                    request,
                    f'Бронирование #{booking.booking_id} создано для существующего гостя {guest.last_name} {guest.first_name}'
                )
            else:
                messages.success(request, f'Бронирование #{booking.booking_id} успешно создано')

            return redirect('/admin-panel/?tab=bookings')

        except Exception as e:
            messages.error(request, f'Ошибка при создании бронирования: {str(e)}')
            return redirect('/admin-panel/?tab=bookings')

    # GET запрос - показываем форму с данными гостя
    room = Room.objects.get(room_id=room_id)

    context = {
        'room': room,
        'check_in': dates['check_in'],
        'check_out': dates['check_out'],
        'guests': dates['guests'],
    }
    return render(request, 'admin_panel/booking_form.html', context)


@login_required
def add_room(request):
    """Добавление нового номера"""
    if request.method == 'POST':
        try:
            room_number = request.POST.get('room_number')
            floor = request.POST.get('floor')
            room_type_id = request.POST.get('room_type_id')
            status = request.POST.get('status', 'available')

            # Проверяем, нет ли уже такого номера
            if Room.objects.filter(room_number=room_number).exists():
                messages.error(request, f'Номер {room_number} уже существует')
            else:
                room = Room.objects.create(
                    room_number=room_number,
                    floor=floor,
                    room_type_id=room_type_id,
                    status=status
                )
                messages.success(request, f'Номер {room_number} успешно добавлен')

        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')

    return redirect('/admin-panel/?tab=rooms')


@login_required
def update_room_status(request, room_id):
    """Обновление статуса номера"""
    if request.method == 'POST':
        try:
            room = Room.objects.get(room_id=room_id)
            new_status = request.POST.get('status')

            # Проверяем, можно ли менять статус
            if new_status == 'maintenance' and room.status == 'occupied':
                messages.error(request, 'Нельзя отправить на ремонт занятый номер')
            else:
                room.status = new_status
                room.save()
                messages.success(request, f'Статус номера {room.room_number} изменен')

        except Exception as e:
            messages.error(request, f'Ошибка: {str(e)}')

    return redirect('/admin-panel/?tab=rooms')


@login_required
def mark_notification_read(request, notif_id):
    """Отметить уведомление как прочитанное"""
    try:
        from booking.models import AdminNotification
        notification = AdminNotification.objects.get(id=notif_id)
        notification.is_read = True
        notification.save()
        messages.success(request, 'Уведомление отмечено как обработанное')
    except:
        pass

    return redirect('/admin-panel/?tab=dashboard')


@login_required
def cancel_booking(request, booking_id):
    """Отмена бронирования"""
    try:
        from booking.models import Booking, AdminNotification
        from django.core.mail import send_mail
        from django.conf import settings

        booking = Booking.objects.select_related('guest', 'room').get(booking_id=booking_id)

        # Запоминаем данные до изменения
        guest_email = booking.guest.email
        guest_name = f"{booking.guest.last_name} {booking.guest.first_name}"
        guest_phone = booking.guest.phone_number
        room_number = booking.room.room_number
        check_in = booking.check_in_date
        check_out = booking.check_out_date

        # Меняем статус брони
        booking.status = 'cancelled'
        booking.save()

        # Освобождаем номер
        room = booking.room
        room.status = 'available'
        room.save()

        # Если есть email - отправляем письмо
        if guest_email:
            try:
                send_mail(
                    'Отмена бронирования',
                    f'''
Здравствуйте, {guest_name}!

Ваше бронирование в отеле "Черное и белое" было отменено.

Детали отменённого бронирования:
────────────────────────────
Номер: {room_number}
Даты: {check_in} - {check_out}

Если вы не запрашивали отмену, свяжитесь с нами.

С уважением,
Отель "Черное и белое"
                    ''',
                    settings.DEFAULT_FROM_EMAIL,
                    [guest_email],
                    fail_silently=False,
                )
                messages.success(request, f'Бронирование #{booking_id} отменено, письмо отправлено клиенту')
            except Exception as e:
                messages.warning(request, f'Бронирование отменено, но не удалось отправить письмо: {str(e)}')

        # Если email нет - создаём уведомление
        else:
            AdminNotification.objects.create(
                notification_type='cancellation',
                message=f'Требуется уведомить клиента об отмене бронирования #{booking_id}',
                guest_name=guest_name,
                guest_phone=guest_phone,
                check_in=check_in,
                check_out=check_out
            )
            messages.warning(request,
                             f'Бронирование #{booking_id} отменено. У клиента нет email - не забудьте позвонить!')

    except Booking.DoesNotExist:
        messages.error(request, 'Бронирование не найдено')
    except Exception as e:
        messages.error(request, f'Ошибка при отмене: {str(e)}')

    return redirect('/admin-panel/?tab=bookings')


@login_required
def mark_notification_read(request, notif_id):
    """Отметить уведомление как прочитанное"""
    try:
        from booking.models import AdminNotification
        notification = AdminNotification.objects.get(id=notif_id)
        notification.is_read = True
        notification.save()
        messages.success(request, 'Уведомление отмечено как обработанное')
    except AdminNotification.DoesNotExist:
        messages.error(request, 'Уведомление не найдено')
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')

    return redirect('/admin-panel/?tab=dashboard')


@login_required
def confirm_booking_admin(request, booking_id):
    """Подтверждение бронирования администратором"""
    try:
        from booking.models import Booking
        from django.core.mail import send_mail
        from django.conf import settings

        booking = Booking.objects.select_related('guest', 'room__room_type').get(booking_id=booking_id)

        # Проверяем, что статус "Новое"
        if booking.status != 'new':
            messages.warning(request, f'Бронирование #{booking_id} уже имеет статус "{booking.get_status_display()}"')
            return redirect('/admin-panel/?tab=bookings')

        # Меняем статус
        booking.status = 'confirmed'
        booking.save()

        # Отправляем письмо гостю о подтверждении
        guest = booking.guest
        room = booking.room

        try:
            subject = f'Подтверждение бронирования #{booking.booking_id}'
            message = f"""
Здравствуйте, {guest.first_name} {guest.last_name}!

Ваше бронирование в отеле "Черное и белое" подтверждено администратором.

Детали бронирования:
─────────────────────
Номер бронирования: #{booking.booking_id}
Номер: {room.room_number} ({room.room_type.type_name})
Дата заезда: {booking.check_in_date}
Дата выезда: {booking.check_out_date}
Количество гостей: {booking.guests_count}
Стоимость: {booking.total_price} руб.

С уважением,
Отель "Черное и белое"
            """
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [guest.email], fail_silently=False)
            messages.success(request, f'Бронирование #{booking_id} подтверждено, письмо отправлено гостю')
        except Exception as e:
            messages.warning(request, f'Бронирование #{booking_id} подтверждено, но письмо не отправлено: {str(e)}')

    except Booking.DoesNotExist:
        messages.error(request, 'Бронирование не найдено')
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')

    return redirect('/admin-panel/?tab=bookings')


@login_required
def checkin_booking(request, booking_id):
    """Регистрация заезда гостя"""
    try:
        from booking.models import Booking
        from django.core.mail import send_mail
        from django.conf import settings

        booking = Booking.objects.select_related('guest', 'room__room_type').get(booking_id=booking_id)

        # Проверяем, что статус "Подтверждено"
        if booking.status != 'confirmed':
            messages.warning(request,
                             f'Бронирование #{booking_id} нельзя заселить (статус: {booking.get_status_display()})')
            return redirect('/admin-panel/?tab=bookings')

        # Меняем статус бронирования
        booking.status = 'checked_in'
        booking.save()

        # Меняем статус номера на "Занят"
        room = booking.room
        room.status = 'occupied'
        room.save()

        # Отправляем письмо гостю о заселении
        guest = booking.guest
        try:
            subject = f'Заселение в отель - бронирование #{booking.booking_id}'
            message = f"""
Здравствуйте, {guest.first_name} {guest.last_name}!

Вы заселились в отель "Черное и белое".

Детали вашего проживания:
─────────────────────────
Номер: {room.room_number} ({room.room_type.type_name})
Дата заезда: {booking.check_in_date}
Дата выезда: {booking.check_out_date}

Желаем приятного отдыха!

С уважением,
Отель "Черное и белое"
            """
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [guest.email], fail_silently=False)
            messages.success(request, f'Заезд по бронированию #{booking_id} зарегистрирован, письмо отправлено гостю')
        except Exception as e:
            messages.warning(request, f'Заезд зарегистрирован, но письмо гостю не отправлено: {str(e)}')

    except Booking.DoesNotExist:
        messages.error(request, 'Бронирование не найдено')
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')

    return redirect('/admin-panel/?tab=bookings')


@login_required
def checkout_booking(request, booking_id):
    """Регистрация выезда гостя"""
    try:
        from booking.models import Booking, AdminNotification
        from django.core.mail import send_mail
        from django.conf import settings
        from datetime import timedelta

        booking = Booking.objects.select_related('guest', 'room__room_type').get(booking_id=booking_id)

        # Проверяем, что статус "Заселился"
        if booking.status != 'checked_in':
            messages.warning(request,
                             f'Бронирование #{booking_id} нельзя выселить (статус: {booking.get_status_display()})')
            return redirect('/admin-panel/?tab=bookings')

        # Меняем статус бронирования
        booking.status = 'checked_out'
        booking.save()

        # Меняем статус номера на "Уборка"
        room = booking.room
        room.status = 'cleaning'
        room.save()

        # Отправляем письмо гостю о выселении
        guest = booking.guest
        try:
            subject = f'Выселение из отеля - бронирование #{booking.booking_id}'
            message = f"""
Здравствуйте, {guest.first_name} {guest.last_name}!

Вы выселились из отеля "Черное и белое".

Благодарим за выбор нашего отеля! Ждём вас снова.

С уважением,
Отель "Черное и белое"
            """
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [guest.email], fail_silently=False)
        except Exception as e:
            print(f"Письмо гостю не отправлено: {e}")

        # Отправляем уведомление клинингу (на email администратора или отдельный email)
        try:
            cleaning_email = getattr(settings, 'CLEANING_EMAIL', settings.ADMIN_EMAIL)
            subject = f'Требуется уборка - номер {room.room_number}'
            message = f"""
Требуется уборка номера {room.room_number} ({room.room_type.type_name}).

Гость выехал {booking.check_out_date}.

Необходимо убраться в номере до приезда следующих гостей.

С уважением,
Система бронирования "Черное и белое"
            """
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [cleaning_email], fail_silently=False)
            messages.success(request, f'Выезд по бронированию #{booking_id} зарегистрирован, клининг уведомлён')
        except Exception as e:
            messages.warning(request, f'Выезд зарегистрирован, но уведомление клинингу не отправлено: {str(e)}')

    except Booking.DoesNotExist:
        messages.error(request, 'Бронирование не найдено')
    except Exception as e:
        messages.error(request, f'Ошибка: {str(e)}')

    return redirect('/admin-panel/?tab=bookings')


@login_required
def delete_room(request, room_id):
    """Удаление номера (только если нет активных бронирований)"""
    try:
        from booking.models import Room, Booking
        from django.db.models import Q

        room = Room.objects.get(room_id=room_id)

        # Проверяем, есть ли активные бронирования (текущие или будущие)
        active_bookings = Booking.objects.filter(
            room_id=room_id,
            status__in=['confirmed', 'checked_in'],  # Подтверждённые и заселённые
            check_out_date__gte=timezone.now().date()  # Выезд ещё не наступил
        ).exists()

        if active_bookings:
            messages.error(request, f'Нельзя удалить номер {room.room_number}: есть активные бронирования')
            return redirect('/admin-panel/?tab=rooms')

        # Проверяем, есть ли будущие бронирования (на любые даты вперёд)
        future_bookings = Booking.objects.filter(
            room_id=room_id,
            check_in_date__gt=timezone.now().date()
        ).exists()

        if future_bookings:
            messages.error(request, f'Нельзя удалить номер {room.room_number}: есть будущие бронирования')
            return redirect('/admin-panel/?tab=rooms')

        # Сохраняем номер для сообщения
        room_number = room.room_number

        # Удаляем номер
        room.delete()

        messages.success(request, f'Номер {room_number} успешно удалён')

    except Room.DoesNotExist:
        messages.error(request, 'Номер не найден')
    except Exception as e:
        messages.error(request, f'Ошибка при удалении: {str(e)}')

    return redirect('/admin-panel/?tab=rooms')