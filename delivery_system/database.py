import sqlite3
import json
import os
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from models import Customer, Order, OrderItem, OrderStatus
from logger_config import logger


class DatabaseInterface(ABC):
    """интерфейс для работы с БД"""
    
    @abstractmethod
    def connect(self):
        pass
    
    @abstractmethod
    def disconnect(self):
        pass
    
    # Клиенты
    @abstractmethod
    def create_customer(self, customer: Customer) -> Customer:
        pass
    
    @abstractmethod
    def get_customer(self, customer_id: int) -> Optional[Customer]:
        pass
    
    @abstractmethod
    def get_all_customers(self) -> List[Customer]:
        pass
    
    @abstractmethod
    def update_customer(self, customer: Customer) -> Customer:
        pass
    
    @abstractmethod
    def delete_customer(self, customer_id: int) -> bool:
        pass
    
    # Заказы
    @abstractmethod
    def create_order(self, order: Order) -> Order:
        pass
    
    @abstractmethod
    def get_order(self, order_id: int) -> Optional[Order]:
        pass
    
    @abstractmethod
    def get_all_orders(self) -> List[Order]:
        pass
    
    @abstractmethod
    def update_order(self, order: Order) -> Order:
        pass
    
    @abstractmethod
    def delete_order(self, order_id: int) -> bool:
        pass
    
    @abstractmethod
    def get_orders_by_status(self, status: str) -> List[Order]:
        pass
    
    @abstractmethod
    def get_orders_by_date_range(self, start_date: str, end_date: str) -> List[Order]:
        pass


class SQLiteDatabase(DatabaseInterface):
    """работа с SQLite"""
    
    def __init__(self, db_path: str = 'data/delivery.db'):
        self.db_path = db_path
        self.conn = None
        
        # Создаем папку data если не существует
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
    
    def connect(self):
        """Подключение к БД"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._create_tables()
        logger.info(f"Подключено к SQLite: {self.db_path}")
    
    def disconnect(self):
        """Отключение от БД"""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Отключено от SQLite")
    
    def _create_tables(self):
        """Создание таблиц"""
        cursor = self.conn.cursor()
        
        # Таблица клиентов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                address TEXT
            )
        ''')
        
        # Таблица заказов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                order_date TEXT NOT NULL,
                status TEXT CHECK(status IN ('новый', 'в доставке', 'выполнен', 'отменён')) NOT NULL,
                total REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT
            )
        ''')
        
        # Таблица позиций заказа
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
            )
        ''')
        
        self.conn.commit()
        logger.debug("Таблицы созданы/проверены")
    
    # ===== Клиенты =====
    
    def create_customer(self, customer: Customer) -> Customer:
        """Создание клиента"""
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO customers (name, phone, address) VALUES (?, ?, ?)',
            (customer.name, customer.phone, customer.address)
        )
        self.conn.commit()
        customer.id = cursor.lastrowid
        logger.info(f"Создан клиент: {customer.name} (ID: {customer.id})")
        return customer
    
    def get_customer(self, customer_id: int) -> Optional[Customer]:
        """Получение клиента по ID"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM customers WHERE id = ?', (customer_id,))
        row = cursor.fetchone()
        if row:
            return Customer(
                id=row['id'],
                name=row['name'],
                phone=row['phone'] or '',
                address=row['address'] or ''
            )
        return None
    
    def get_all_customers(self) -> List[Customer]:
        """Получение всех клиентов"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM customers')
        rows = cursor.fetchall()
        return [
            Customer(
                id=row['id'],
                name=row['name'],
                phone=row['phone'] or '',
                address=row['address'] or ''
            )
            for row in rows
        ]
    
    def update_customer(self, customer: Customer) -> Customer:
        """Обновление клиента"""
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE customers SET name=?, phone=?, address=? WHERE id=?',
            (customer.name, customer.phone, customer.address, customer.id)
        )
        self.conn.commit()
        logger.info(f"Обновлен клиент: {customer.name} (ID: {customer.id})")
        return customer
    
    def delete_customer(self, customer_id: int) -> bool:
        """Удаление клиента"""
        # Проверяем есть ли заказы
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM orders WHERE customer_id = ?', (customer_id,))
        count = cursor.fetchone()[0]
        
        if count > 0:
            logger.warning(f"Нельзя удалить клиента {customer_id}: есть заказы")
            return False
        
        cursor.execute('DELETE FROM customers WHERE id = ?', (customer_id,))
        self.conn.commit()
        logger.info(f"Удален клиент: ID {customer_id}")
        return True
    
    #  Заказы 
    
    def create_order(self, order: Order) -> Order:
        """Создание заказа"""
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO orders (customer_id, order_date, status, total) VALUES (?, ?, ?, ?)',
            (order.customer_id, order.order_date, order.status, order.total)
        )
        self.conn.commit()
        order.id = cursor.lastrowid
        
        # Сохраняем позиции
        for item in order.items:
            item.order_id = order.id
            cursor.execute(
                'INSERT INTO order_items (order_id, product_name, quantity, price) VALUES (?, ?, ?, ?)',
                (item.order_id, item.product_name, item.quantity, item.price)
            )
            item.id = cursor.lastrowid
        
        self.conn.commit()
        logger.info(f"Создан заказ: ID {order.id} с {len(order.items)} позициями")
        return order
    
    def get_order(self, order_id: int) -> Optional[Order]:
        """Получение заказа по ID с позициями"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        # Получаем позиции заказа
        cursor.execute('SELECT * FROM order_items WHERE order_id = ?', (order_id,))
        items_rows = cursor.fetchall()
        
        items = []
        for item_row in items_rows:
            item = OrderItem(
                id=item_row['id'],
                order_id=item_row['order_id'],
                product_name=item_row['product_name'],
                quantity=item_row['quantity'],
                price=item_row['price']
            )
            items.append(item)
        
        logger.debug(f"Заказ {order_id}: загружено {len(items)} позиций")
        
        return Order(
            id=row['id'],
            customer_id=row['customer_id'],
            order_date=row['order_date'],
            status=row['status'],
            total=row['total'],
            items=items
        )
    
    def get_all_orders(self) -> List[Order]:
        """Получение всех заказов с позициями"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM orders')
        rows = cursor.fetchall()
        
        orders = []
        for row in rows:
            cursor.execute('SELECT * FROM order_items WHERE order_id = ?', (row['id'],))
            items_rows = cursor.fetchall()
            items = [
                OrderItem(
                    id=item['id'],
                    order_id=item['order_id'],
                    product_name=item['product_name'],
                    quantity=item['quantity'],
                    price=item['price']
                )
                for item in items_rows
            ]
            
            orders.append(Order(
                id=row['id'],
                customer_id=row['customer_id'],
                order_date=row['order_date'],
                status=row['status'],
                total=row['total'],
                items=items
            ))
        
        return orders
    
    def update_order(self, order: Order) -> Order:
        """Обновление заказа"""
        cursor = self.conn.cursor()
        cursor.execute(
            'UPDATE orders SET customer_id=?, order_date=?, status=?, total=? WHERE id=?',
            (order.customer_id, order.order_date, order.status, order.total, order.id)
        )
        
        # Удаляем старые и добавляем новые
        cursor.execute('DELETE FROM order_items WHERE order_id = ?', (order.id,))
        for item in order.items:
            cursor.execute(
                'INSERT INTO order_items (order_id, product_name, quantity, price) VALUES (?, ?, ?, ?)',
                (order.id, item.product_name, item.quantity, item.price)
            )
        
        self.conn.commit()
        logger.info(f"Обновлен заказ: ID {order.id} с {len(order.items)} позициями")
        return order
    
    def delete_order(self, order_id: int) -> bool:
        """Удаление заказа"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM orders WHERE id = ?', (order_id,))
        self.conn.commit()
        logger.info(f"Удален заказ: ID {order_id}")
        return True
    
    def get_orders_by_status(self, status: str) -> List[Order]:
        """Получение заказов по статусу"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM orders WHERE status = ?', (status,))
        rows = cursor.fetchall()
        
        orders = []
        for row in rows:
            cursor.execute('SELECT * FROM order_items WHERE order_id = ?', (row['id'],))
            items_rows = cursor.fetchall()
            items = [
                OrderItem(
                    id=item['id'],
                    order_id=item['order_id'],
                    product_name=item['product_name'],
                    quantity=item['quantity'],
                    price=item['price']
                )
                for item in items_rows
            ]
            
            orders.append(Order(
                id=row['id'],
                customer_id=row['customer_id'],
                order_date=row['order_date'],
                status=row['status'],
                total=row['total'],
                items=items
            ))
        
        return orders
    
    def get_orders_by_date_range(self, start_date: str, end_date: str) -> List[Order]:
        """Получение заказов за период"""
        cursor = self.conn.cursor()
        cursor.execute(
            'SELECT * FROM orders WHERE order_date BETWEEN ? AND ?',
            (start_date, end_date)
        )
        rows = cursor.fetchall()
        
        orders = []
        for row in rows:
            cursor.execute('SELECT * FROM order_items WHERE order_id = ?', (row['id'],))
            items_rows = cursor.fetchall()
            items = [
                OrderItem(
                    id=item['id'],
                    order_id=item['order_id'],
                    product_name=item['product_name'],
                    quantity=item['quantity'],
                    price=item['price']
                )
                for item in items_rows
            ]
            
            orders.append(Order(
                id=row['id'],
                customer_id=row['customer_id'],
                order_date=row['order_date'],
                status=row['status'],
                total=row['total'],
                items=items
            ))
        
        return orders


class TinyDBDatabase(DatabaseInterface):
    """Реализация работы с TinyDB"""
    
    def __init__(self, db_path: str = 'data/tinydb.json'):
        self.db_path = db_path
        self.db = None
        self.customers_table = None
        self.orders_table = None
        
        # Создаем папку data если не существует
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
    
    def connect(self):
        """Подключение к БД"""
        try:
            from tinydb import TinyDB, Query
        except ImportError:
            raise ImportError("TinyDB не установлен. Установите: pip install tinydb")
        
        self.db = TinyDB(self.db_path)
        self.customers_table = self.db.table('customers')
        self.orders_table = self.db.table('orders')
        self.Query = Query
        logger.info(f"Подключено к TinyDB: {self.db_path}")
    
    def disconnect(self):
        """Отключение от БД"""
        if self.db:
            self.db.close()
            self.db = None
            logger.info("Отключено от TinyDB")
    
    # Клиенты 
    
    def create_customer(self, customer: Customer) -> Customer:
        """Создание клиента"""
        customer_data = customer.to_dict()
        if customer_data.get('id'):
            del customer_data['id']
        
        doc_id = self.customers_table.insert(customer_data)
        customer.id = doc_id
        logger.info(f"Создан клиент: {customer.name} (ID: {customer.id})")
        return customer
    
    def get_customer(self, customer_id: int) -> Optional[Customer]:
        """Получение клиента по ID"""
        result = self.customers_table.get(doc_id=customer_id)
        if result:
            return Customer.from_dict(result)
        return None
    
    def get_all_customers(self) -> List[Customer]:
        """Получение всех клиентов"""
        results = self.customers_table.all()
        return [Customer.from_dict(r) for r in results]
    
    def update_customer(self, customer: Customer) -> Customer:
        """Обновление клиента"""
        customer_data = customer.to_dict()
        self.customers_table.update(customer_data, doc_ids=[customer.id])
        logger.info(f"Обновлен клиент: {customer.name} (ID: {customer.id})")
        return customer
    
    def delete_customer(self, customer_id: int) -> bool:
        """Удаление клиента"""
        # Проверяем есть ли заказы
        orders = self.get_all_orders()
        has_orders = any(o.customer_id == customer_id for o in orders)
        
        if has_orders:
            logger.warning(f"Нельзя удалить клиента {customer_id}: есть заказы")
            return False
        
        self.customers_table.remove(doc_ids=[customer_id])
        logger.info(f"Удален клиент: ID {customer_id}")
        return True
    
    # Заказы
    
    def create_order(self, order: Order) -> Order:
        """Создание заказа"""
        order_data = order.to_dict()
        if order_data.get('id'):
            del order_data['id']
        
        doc_id = self.orders_table.insert(order_data)
        order.id = doc_id
        
        # Обновляем ID в элементах
        for item in order.items:
            item.order_id = doc_id
        
        logger.info(f"Создан заказ: ID {order.id} с {len(order.items)} позициями")
        return order
    
    def get_order(self, order_id: int) -> Optional[Order]:
        """Получение заказа по ID"""
        result = self.orders_table.get(doc_id=order_id)
        if result:
            order = Order.from_dict(result)
            logger.debug(f"Заказ {order_id}: загружено {len(order.items)} позиций")
            return order
        return None
    
    def get_all_orders(self) -> List[Order]:
        """Получение всех заказов"""
        results = self.orders_table.all()
        return [Order.from_dict(r) for r in results]
    
    def update_order(self, order: Order) -> Order:
        """Обновление заказа"""
        order_data = order.to_dict()
        self.orders_table.update(order_data, doc_ids=[order.id])
        logger.info(f"Обновлен заказ: ID {order.id} с {len(order.items)} позициями")
        return order
    
    def delete_order(self, order_id: int) -> bool:
        """Удаление заказа"""
        self.orders_table.remove(doc_ids=[order_id])
        logger.info(f"Удален заказ: ID {order_id}")
        return True
    
    def get_orders_by_status(self, status: str) -> List[Order]:
        """Получение заказов по статусу"""
        results = self.orders_table.search(self.Query().status == status)
        return [Order.from_dict(r) for r in results]
    
    def get_orders_by_date_range(self, start_date: str, end_date: str) -> List[Order]:
        """Получение заказов за период"""
        results = self.orders_table.search(
            (self.Query().order_date >= start_date) & 
            (self.Query().order_date <= end_date)
        )
        return [Order.from_dict(r) for r in results]


class DatabaseFactory:
    """Фабрика для создания БД"""
    
    @staticmethod
    def create(db_type: str = 'sqlite', **kwargs) -> DatabaseInterface:

        if db_type.lower() == 'sqlite':
            return SQLiteDatabase(kwargs.get('db_path', 'data/delivery.db'))
        elif db_type.lower() == 'tinydb':
            return TinyDBDatabase(kwargs.get('db_path', 'data/tinydb.json'))
        else:
            raise ValueError(f"Неподдерживаемый тип БД: {db_type}")