import pg8000

DB_NAME = 'hotel_bookings'
DB_USER = 'postgres'
DB_PASSWORD = '123'
DB_HOST = 'localhost'
DB_PORT = 5432

try:
    # Подключаемся к базе
    conn = pg8000.connect(
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    cursor = conn.cursor()

    # 1. Проверка подключения
    cursor.execute("SELECT 1;")
    result = cursor.fetchone()
    print("Подключение успешно! Результат запроса:", result[0])
    print("-" * 50)

    # 2. Получаем список всех таблиц в базе
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    tables = cursor.fetchall()

    print("Таблицы в базе данных:")
    for table in tables:
        print(f"  • {table[0]}")
    print("-" * 50)

    # 3. Для каждой таблицы показываем её структуру (колонки)
    for table in tables:
        table_name = table[0]
        print(f"Структура таблицы '{table_name}':")

        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position;
        """, (table_name,))

        columns = cursor.fetchall()
        for col in columns:
            col_name, data_type, is_nullable, default = col
            nullable_symbol = "NULL" if is_nullable == "YES" else "NOT NULL"
            default_info = f"default: {default}" if default else ""
            print(f"    ├─ {col_name}: {data_type} {nullable_symbol} {default_info}")
        print()

    cursor.close()
    conn.close()
    print("Соединение закрыто.")

except Exception as e:
    print("Ошибка подключения:", e)