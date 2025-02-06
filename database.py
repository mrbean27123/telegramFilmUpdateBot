import time
import psycopg2
from psycopg2.extras import DictCursor
from loguru import logger

import message


class Database:
    # Параметры подключения
    host = 'DB_HOST'
    user = 'DB_USER'
    password = 'DB_PASSWORD'
    port = "DB_PORT"
    dbname = 'DB_NAME'

    def _create_connection(self):
        return psycopg2.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            port=self.port,
            dbname=self.dbname
        )

    def __init__(self):
        self.connection = None
        try:
            self.connection = self._create_connection()
            self.connection.autocommit = True
            logger.success("Успешное подключение к базе данных")
        except Exception as e:
            logger.warning(f"Ошибка подключения к базе данных: {e}")
            # Восстанавливаем соединение
            self.reconnect()

    def ensure_connection(self):
        """
        Проверяет, активно ли соединение с базой данных, и восстанавливает его при необходимости.
        """
        if self.connection is None:
            self.reconnect()
            return
        try:
            # Проверяем активность соединения с помощью простого запроса
            with self.connection.cursor() as cursor:
                cursor.execute('SELECT 1')
        except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
            # Логируем потерю соединения
            logger.warning(f"Соединение с базой данных потеряно: {e}")
            # Восстанавливаем соединение
            self.reconnect()

    def reconnect(self, retries=15, delay=2):
        """
        Восстанавливает соединение с базой данных.
        """
        if self.connection:
            try:
                self.connection.close()
            except Exception as close_error:
                logger.warning(f"Ошибка при закрытии старого соединения: {close_error}")
        for attempt in range(retries):
            try:
                self.connection = self._create_connection()
                self.connection.autocommit = True
                logger.info("Подключение к базе данных восстановлено")
                return  # Успешное подключение, выходим из функции
            except Exception as e:
                logger.warning(f"Попытка {attempt + 1} из {retries} не удалась: {e}")
                time.sleep(delay)  # Задержка перед повтором

        # Если все попытки провалились, записываем ошибку
        message.send_report("Не удалось восстановить соединение с базой данных после нескольких попыток.")

    def create_table(self, table_name):
        self.ensure_connection()  # Проверяем соединение перед использованием
        with self.connection.cursor(cursor_factory=DictCursor) as cursor:
            if not self.table_exists(table_name):
                cursor.execute(f"""
                    CREATE TABLE {table_name} 
                    (
                        id SERIAL PRIMARY KEY,
                        title TEXT NOT NULL,
                        title_original TEXT,
                        year_start INT,
                        year_end INT,
                        categories TEXT[],
                        rating FLOAT,
                        description TEXT,
                        country TEXT[],
                        url TEXT,
                        date_now TIMESTAMPTZ
                    )
                """)
                self.connection.commit()  # Сохранение изменений в базе данных
                logger.success(f"Таблица '{table_name}' создана")

    def table_exists(self, table_name):
        self.ensure_connection()  # Проверяем соединение перед использованием
        with self.connection.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute(
                """SELECT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = %s)""", (table_name,)
            )
            result = cursor.fetchone()
            return result['exists']

    def add_into_table(self, table_name, data):
        """
        Добавить новую запись в таблицу.
        :param table_name: Название таблицы.
        :param data: Словарь данных для вставки {col_name: value}.
        :return: ID вставленной записи (если применимо) или количество вставленных строк.
        """
        if not data:
            raise ValueError("Необходимо указать данные для вставки.")

        self.ensure_connection()
        with self.connection.cursor(cursor_factory=DictCursor) as cursor:
            # Генерация частей SQL-запроса
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["%s"] * len(data))
            values = list(data.values())

            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders}) RETURNING id"
            cursor.execute(query, values)
            self.connection.commit()

            # Если есть возвращаемый ID, его можно получить
            result = cursor.fetchone()
            return result['id'] if result and 'id' in result else cursor.rowcount

    def delete_from_table(self, table_name, data):
        """
        Удалить записи из таблицы с указанными фильтрами.
        :param table_name: Название таблицы.
        :param data: Словарь фильтров {col_name: value}.
        :return: Количество удаленных строк.
        """
        if not data:
            raise ValueError("Необходимо указать фильтры для удаления.")

        self.ensure_connection()
        with self.connection.cursor(cursor_factory=DictCursor) as cursor:
            # Генерация частей SQL-запроса
            where_clause = " AND ".join([f"{key} = %s" for key in data.keys()])
            params = list(data.values())

            query = f"DELETE FROM {table_name} WHERE {where_clause}"
            cursor.execute(query, params)
            self.connection.commit()
            return cursor.rowcount

    def get_table(self, table_name, data=None, sort_by=None):
        """
        Получить данные из таблицы с указанными фильтрами и сортировкой.
        :param table_name: Название таблицы.
        :param data: Словарь фильтров {col_name: (operator, value)}, опционально.
                     Например: {"date_now": (">=", some_date)}.
        :param sort_by: Строка для сортировки, например "id ASC" или "rating DESC".
        :return: Список словарей с результатами.
        """
        self.ensure_connection()
        with self.connection.cursor(cursor_factory=DictCursor) as cursor:
            where_clause = ""
            params = []
            if data:
                filter_clauses = []
                for key, condition in data.items():
                    if isinstance(condition, tuple):
                        operator, value = condition
                        filter_clauses.append(f"{key} {operator} %s")
                        params.append(value)
                    elif condition is None:  # Обрабатываем фильтры с None как IS NULL
                        filter_clauses.append(f"{key} IS NULL")
                    else:
                        filter_clauses.append(f"{key} = %s")
                        params.append(condition)
                where_clause = " WHERE " + " AND ".join(filter_clauses)

            order_by_clause = f" ORDER BY {sort_by}" if sort_by else ""

            query = f"SELECT * FROM {table_name}{where_clause}{order_by_clause}"
            cursor.execute(query, params)
            return cursor.fetchall()

    def update_table(self, table_name, data, updates):
        """
        Обновить записи в таблице с указанными фильтрами.
        :param table_name: Название таблицы.
        :param data: Словарь фильтров {col_name: value}.
        :param updates: Словарь обновляемых данных {col_name: value}.
        :return: Количество измененных строк.
        """
        if not updates:
            raise ValueError("Необходимо указать данные для обновления.")

        self.ensure_connection()
        with self.connection.cursor(cursor_factory=DictCursor) as cursor:
            # Генерация частей SQL-запроса
            set_clause = ", ".join([f"{key} = %s" for key in updates.keys()])
            where_clause = " AND ".join([f"{key} = %s" for key in data.keys()])

            query = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
            params = list(updates.values()) + list(data.values())

            cursor.execute(query, params)
            self.connection.commit()
            return cursor.rowcount


db = Database()


if __name__ == "__main__":
    pass
