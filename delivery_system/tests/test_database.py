import pytest
import os
import tempfile
import shutil
from database import SQLiteDatabase, TinyDBDatabase, DatabaseFactory
from models import Customer, Order, OrderItem, OrderStatus


class DatabaseTestMixin:
    """Миксин с общими тестами для всех баз данных"""
    
    db = None
    
    def setup_method(self):
        """Подготовка перед каждым тестом"""
        self.db.connect()
    
    def teardown_method(self):
        """Очистка после каждого теста"""
        self.db.disconnect()
    
    # ===== Тесты клиентов =====
    
    def test_create_customer(self):
        """Создание клиента"""
        customer = Customer(name="Иван Петров", phone="+79991234567", address="г. Москва")
        result = self.db.create_customer(customer)
        
        assert result.id is not None
        assert result.name == "Иван Петров"
    
    def test_get_customer(self):
        """Получение клиента по ID"""
        customer = Customer(name="Иван Петров")
        customer = self.db.create_customer(customer)
        
        result = self.db.get_customer(customer.id)
        
        assert result is not None
        assert result.id == customer.id
        assert result.name == "Иван Петров"
    
    def test_get_nonexistent_customer(self):
        """Получение несуществующего клиента"""
        result = self.db.get_customer(9999)
        assert result is None
    
    def test_get_all_customers(self):
        """Получение всех клиентов"""
        self.db.create_customer(Customer(name="Клиент 1"))
        self.db.create_customer(Customer(name="Клиент 2"))
        
        customers = self.db.get_all_customers()
        
        assert len(customers) == 2
    
    def test_update_customer(self):
        """Обновление клиента"""
        customer = Customer(name="Иван Петров")
        customer = self.db.create_customer(customer)
        
        customer.name = "Петр Иванов"
        customer.phone = "+79997654321"
        result = self.db.update_customer(customer)
        
        assert result.name == "Петр Иванов"
        assert result.phone == "+79997654321"
    
    def test_delete_customer_success(self):
        """Успешное удаление клиента"""
        customer = Customer(name="Иван Петров")
        customer = self.db.create_customer(customer)
        
        result = self.db.delete_customer(customer.id)
        
        assert result is True
        assert self.db.get_customer(customer.id) is None
    
    def test_delete_customer_with_orders_fails(self):
        """Нельзя удалить клиента с заказами"""
        # Создаем клиента
        customer = Customer(name="Иван Петров")
        customer = self.db.create_customer(customer)
        
        # Создаем заказ для этого клиента
        order = Order(
            customer_id=customer.id,
            order_date="2025-06-17",
            status="новый"
        )
        self.db.create_order(order)
        
        # Пытаемся удалить клиента
        result = self.db.delete_customer(customer.id)
        
        assert result is False
        assert self.db.get_customer(customer.id) is not None
    
    # ===== Тесты заказов =====
    
    def test_create_order(self):
        """Создание заказа"""
        customer = Customer(name="Иван Петров")
        customer = self.db.create_customer(customer)
        
        order = Order(
            customer_id=customer.id,
            order_date="2025-06-17",
            status="новый"
        )
        result = self.db.create_order(order)
        
        assert result.id is not None
        assert result.customer_id == customer.id
    
    def test_create_order_with_items(self):
        """Создание заказа с позициями"""
        customer = Customer(name="Иван Петров")
        customer = self.db.create_customer(customer)
        
        items = [
            OrderItem(product_name="Пицца", quantity=2, price=500.0),
            OrderItem(product_name="Суши", quantity=1, price=300.0)
        ]
        order = Order(
            customer_id=customer.id,
            order_date="2025-06-17",
            items=items
        )
        result = self.db.create_order(order)
        
        assert result.id is not None
        assert len(result.items) == 2
        assert result.total == 1300.0
    
    def test_get_order(self):
        """Получение заказа по ID"""
        customer = Customer(name="Иван Петров")
        customer = self.db.create_customer(customer)
        
        order = Order(customer_id=customer.id, order_date="2025-06-17")
        order = self.db.create_order(order)
        
        result = self.db.get_order(order.id)
        
        assert result is not None
        assert result.id == order.id
    
    def test_get_nonexistent_order(self):
        """Получение несуществующего заказа"""
        result = self.db.get_order(9999)
        assert result is None
    
    def test_get_all_orders(self):
        """Получение всех заказов"""
        customer = Customer(name="Иван Петров")
        customer = self.db.create_customer(customer)
        
        self.db.create_order(Order(customer_id=customer.id, order_date="2025-06-17"))
        self.db.create_order(Order(customer_id=customer.id, order_date="2025-06-18"))
        
        orders = self.db.get_all_orders()
        
        assert len(orders) == 2
    
    def test_update_order(self):
        """Обновление заказа"""
        customer = Customer(name="Иван Петров")
        customer = self.db.create_customer(customer)
        
        order = Order(customer_id=customer.id, order_date="2025-06-17", status="новый")
        order = self.db.create_order(order)
        
        order.status = "в доставке"
        result = self.db.update_order(order)
        
        assert result.status == "в доставке"
    
    def test_delete_order(self):
        """Удаление заказа"""
        customer = Customer(name="Иван Петров")
        customer = self.db.create_customer(customer)
        
        order = Order(customer_id=customer.id, order_date="2025-06-17")
        order = self.db.create_order(order)
        
        result = self.db.delete_order(order.id)
        
        assert result is True
        assert self.db.get_order(order.id) is None
    
    def test_get_orders_by_status(self):
        """Получение заказов по статусу"""
        customer = Customer(name="Иван Петров")
        customer = self.db.create_customer(customer)
        
        self.db.create_order(Order(customer_id=customer.id, order_date="2025-06-17", status="новый"))
        self.db.create_order(Order(customer_id=customer.id, order_date="2025-06-18", status="новый"))
        self.db.create_order(Order(customer_id=customer.id, order_date="2025-06-19", status="выполнен"))
        
        new_orders = self.db.get_orders_by_status("новый")
        completed_orders = self.db.get_orders_by_status("выполнен")
        
        assert len(new_orders) == 2
        assert len(completed_orders) == 1
    
    def test_get_orders_by_date_range(self):
        """Получение заказов за период"""
        customer = Customer(name="Иван Петров")
        customer = self.db.create_customer(customer)
        
        self.db.create_order(Order(customer_id=customer.id, order_date="2025-06-15", status="новый"))
        self.db.create_order(Order(customer_id=customer.id, order_date="2025-06-17", status="новый"))
        self.db.create_order(Order(customer_id=customer.id, order_date="2025-06-20", status="новый"))
        
        orders = self.db.get_orders_by_date_range("2025-06-16", "2025-06-18")
        
        assert len(orders) == 1
        assert orders[0].order_date == "2025-06-17"


class TestSQLiteDatabase(DatabaseTestMixin):
    """Тесты для SQLite базы данных"""
    
    def setup_method(self):
        """Создание временной БД для тестов"""
        self.temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(self.temp_dir, 'test.db')
        self.db = SQLiteDatabase(db_path)
        super().setup_method()
    
    def teardown_method(self):
        """Удаление временной БД"""
        super().teardown_method()
        shutil.rmtree(self.temp_dir)


class TestTinyDBDatabase(DatabaseTestMixin):
    """Тесты для TinyDB базы данных"""
    
    def setup_method(self):
        """Создание временной БД для тестов"""
        self.temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(self.temp_dir, 'test.json')
        self.db = TinyDBDatabase(db_path)
        super().setup_method()
    
    def teardown_method(self):
        """Удаление временной БД"""
        super().teardown_method()
        shutil.rmtree(self.temp_dir)


class TestDatabaseFactory:
    """Тесты для фабрики баз данных"""
    
    def test_create_sqlite_database(self):
        """Создание SQLite базы данных"""
        db = DatabaseFactory.create('sqlite', db_path=':memory:')
        assert isinstance(db, SQLiteDatabase)
    
    def test_create_tinydb_database(self):
        """Создание TinyDB базы данных"""
        temp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(temp_dir, 'test.json')
            db = DatabaseFactory.create('tinydb', db_path=db_path)
            assert isinstance(db, TinyDBDatabase)
        finally:
            shutil.rmtree(temp_dir)
    
    def test_create_invalid_database(self):
        """Создание базы данных с неверным типом"""
        with pytest.raises(ValueError, match="Неподдерживаемый тип БД"):
            DatabaseFactory.create('invalid_type')