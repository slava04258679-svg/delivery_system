import pytest
import tempfile
import shutil
import os
from database import SQLiteDatabase, TinyDBDatabase
from models import Customer, Order, OrderItem


@pytest.fixture
def temp_sqlite_db():
    """Фикстура для создания временной SQLite БД"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test.db')
    db = SQLiteDatabase(db_path)
    db.connect()
    
    yield db
    
    db.disconnect()
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_tinydb():
    """Фикстура для создания временной TinyDB"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, 'test.json')
    db = TinyDBDatabase(db_path)
    db.connect()
    
    yield db
    
    db.disconnect()
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_customer():
    """Фикстура с тестовым клиентом"""
    return Customer(
        name="Иван Петров",
        phone="+79991234567",
        address="г. Москва, ул. Ленина, 1"
    )


@pytest.fixture
def sample_order(sample_customer, temp_sqlite_db):
    """Фикстура с тестовым заказом"""
    customer = temp_sqlite_db.create_customer(sample_customer)
    
    items = [
        OrderItem(product_name="Пицца Маргарита", quantity=2, price=500.0),
        OrderItem(product_name="Суши Филадельфия", quantity=1, price=600.0)
    ]
    
    order = Order(
        customer_id=customer.id,
        order_date="2025-06-17",
        status="новый",
        items=items
    )
    
    return temp_sqlite_db.create_order(order)