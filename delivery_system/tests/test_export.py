import pytest
import os
import tempfile
import shutil
import json
import xml.etree.ElementTree as ET

from database import SQLiteDatabase
from models import Customer, Order, OrderItem
from data_export import DataExporter, DataImporter, export_data, import_data


class TestDataExporter:
    """Тесты для экспорта данных"""
    
    @pytest.fixture
    def db_with_data(self):
        """Создание БД с тестовыми данными"""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'test.db')
        db = SQLiteDatabase(db_path)
        db.connect()
        
        # Создаем клиента
        customer = Customer(name="Иван Петров", phone="+79991234567", address="г. Москва")
        customer = db.create_customer(customer)
        
        # Создаем заказ
        items = [
            OrderItem(product_name="Пицца", quantity=2, price=500.0),
            OrderItem(product_name="Суши", quantity=1, price=300.0)
        ]
        order = Order(
            customer_id=customer.id,
            order_date="2025-06-17",
            status="новый",
            items=items
        )
        db.create_order(order)
        
        yield db, temp_dir
        
        db.disconnect()
        shutil.rmtree(temp_dir)
    
    def test_export_to_json(self, db_with_data):
        """Экспорт в JSON"""
        db, temp_dir = db_with_data
        filepath = os.path.join(temp_dir, 'export.json')
        
        exporter = DataExporter(db)
        result = exporter.export_to_json(filepath)
        
        assert result is True
        assert os.path.exists(filepath)
        
        # Проверяем содержимое
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert 'orders' in data
        assert 'customers' in data
        assert len(data['orders']) == 1
        assert len(data['customers']) == 1
    
    def test_export_to_xml(self, db_with_data):
        """Экспорт в XML"""
        db, temp_dir = db_with_data
        filepath = os.path.join(temp_dir, 'export.xml')
        
        exporter = DataExporter(db)
        result = exporter.export_to_xml(filepath)
        
        assert result is True
        assert os.path.exists(filepath)
        
        # Проверяем структуру XML
        tree = ET.parse(filepath)
        root = tree.getroot()
        
        assert root.tag == 'delivery_data'
        assert root.find('orders') is not None
        assert root.find('customers') is not None
    
    def test_export_to_json_empty_db(self):
        """Экспорт из пустой БД"""
        temp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(temp_dir, 'test.db')
            db = SQLiteDatabase(db_path)
            db.connect()
            
            filepath = os.path.join(temp_dir, 'export.json')
            exporter = DataExporter(db)
            result = exporter.export_to_json(filepath)
            
            assert result is True
            assert os.path.exists(filepath)
            
            db.disconnect()
        finally:
            shutil.rmtree(temp_dir)


class TestDataImporter:
    """Тесты для импорта данных"""
    
    def test_import_from_json(self):
        """Импорт из JSON"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Создаем тестовый JSON файл
            json_data = {
                'customers': [
                    {'id': 1, 'name': 'Иван Петров', 'phone': '+79991234567', 'address': 'г. Москва'}
                ],
                'orders': [
                    {
                        'id': 1,
                        'customer_id': 1,
                        'order_date': '2025-06-17',
                        'status': 'новый',
                        'total': 1300.0,
                        'items': [
                            {'product_name': 'Пицца', 'quantity': 2, 'price': 500.0},
                            {'product_name': 'Суши', 'quantity': 1, 'price': 300.0}
                        ]
                    }
                ]
            }
            
            json_path = os.path.join(temp_dir, 'import.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            # Создаем БД и импортируем
            db_path = os.path.join(temp_dir, 'test.db')
            db = SQLiteDatabase(db_path)
            db.connect()
            
            importer = DataImporter(db)
            result = importer.import_from_json(json_path)
            
            assert result['success'] is True
            assert result['customers_imported'] == 1
            assert result['orders_imported'] == 1
            
            # Проверяем что данные импортированы
            orders = db.get_all_orders()
            assert len(orders) == 1
            assert len(orders[0].items) == 2
            
            db.disconnect()
        finally:
            shutil.rmtree(temp_dir)
    
    def test_import_from_xml(self):
        """Импорт из XML"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Создаем тестовый XML файл
            xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<delivery_data export_date="2025-06-17T10:00:00">
  <customers>
    <customer id="1">
      <name>Иван Петров</name>
      <phone>+79991234567</phone>
      <address>г. Москва</address>
    </customer>
  </customers>
  <orders>
    <order id="1">
      <customer_id>1</customer_id>
      <order_date>2025-06-17</order_date>
      <status>новый</status>
      <total>1300.0</total>
      <items>
        <item>
          <product_name>Пицца</product_name>
          <quantity>2</quantity>
          <price>500.0</price>
        </item>
        <item>
          <product_name>Суши</product_name>
          <quantity>1</quantity>
          <price>300.0</price>
        </item>
      </items>
    </order>
  </orders>
</delivery_data>'''
            
            xml_path = os.path.join(temp_dir, 'import.xml')
            with open(xml_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            
            # Создаем БД и импортируем
            db_path = os.path.join(temp_dir, 'test.db')
            db = SQLiteDatabase(db_path)
            db.connect()
            
            importer = DataImporter(db)
            result = importer.import_from_xml(xml_path)
            
            assert result['success'] is True
            assert result['customers_imported'] == 1
            assert result['orders_imported'] == 1
            
            db.disconnect()
        finally:
            shutil.rmtree(temp_dir)
    
    def test_import_skip_existing(self):
        """Пропуск существующих заказов"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Создаем JSON с заказом
            json_data = {
                'customers': [
                    {'id': 1, 'name': 'Иван Петров', 'phone': '+79991234567', 'address': 'г. Москва'}
                ],
                'orders': [
                    {
                        'id': 1,
                        'customer_id': 1,
                        'order_date': '2025-06-17',
                        'status': 'новый',
                        'total': 1000.0,
                        'items': []
                    }
                ]
            }
            
            json_path = os.path.join(temp_dir, 'import.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            # Создаем БД
            db_path = os.path.join(temp_dir, 'test.db')
            db = SQLiteDatabase(db_path)
            db.connect()
            
            # Импортируем первый раз
            importer = DataImporter(db)
            result1 = importer.import_from_json(json_path, skip_existing=True)
            assert result1['orders_imported'] == 1
            
            # Импортируем второй раз
            result2 = importer.import_from_json(json_path, skip_existing=True)
            assert result2['orders_skipped'] == 1
            
            db.disconnect()
        finally:
            shutil.rmtree(temp_dir)
    
    def test_import_file_not_found(self):
        """Импорт несуществующего файла"""
        temp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(temp_dir, 'test.db')
            db = SQLiteDatabase(db_path)
            db.connect()
            
            importer = DataImporter(db)
            result = importer.import_from_json('/nonexistent/file.json')
            
            assert result['success'] is False
            assert len(result['errors']) > 0
            
            db.disconnect()
        finally:
            shutil.rmtree(temp_dir)
    
    def test_import_invalid_json_structure(self):
        """Импорт JSON с неверной структурой"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Создаем неверный JSON
            json_path = os.path.join(temp_dir, 'invalid.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump({'invalid': 'data'}, f)
            
            db_path = os.path.join(temp_dir, 'test.db')
            db = SQLiteDatabase(db_path)
            db.connect()
            
            importer = DataImporter(db)
            result = importer.import_from_json(json_path)
            
            assert result['success'] is False
            
            db.disconnect()
        finally:
            shutil.rmtree(temp_dir)


class TestConvenienceFunctions:
    """Тесты для удобных функций экспорта/импорта"""
    
    def test_export_data_json(self):
        """Экспорт через удобную функцию (JSON)"""
        temp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(temp_dir, 'test.db')
            db = SQLiteDatabase(db_path)
            db.connect()
            
            filepath = os.path.join(temp_dir, 'export.json')
            result = export_data(db, filepath, 'json')
            
            assert result is True
            assert os.path.exists(filepath)
            
            db.disconnect()
        finally:
            shutil.rmtree(temp_dir)
    
    def test_export_data_xml(self):
        """Экспорт через удобную функцию (XML)"""
        temp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(temp_dir, 'test.db')
            db = SQLiteDatabase(db_path)
            db.connect()
            
            filepath = os.path.join(temp_dir, 'export.xml')
            result = export_data(db, filepath, 'xml')
            
            assert result is True
            assert os.path.exists(filepath)
            
            db.disconnect()
        finally:
            shutil.rmtree(temp_dir)
    
    def test_import_data_json(self):
        """Импорт через удобную функцию (JSON)"""
        temp_dir = tempfile.mkdtemp()
        try:
            # Создаем JSON
            json_data = {
                'customers': [{'id': 1, 'name': 'Тест', 'phone': '', 'address': ''}],
                'orders': []
            }
            json_path = os.path.join(temp_dir, 'import.json')
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f)
            
            db_path = os.path.join(temp_dir, 'test.db')
            db = SQLiteDatabase(db_path)
            db.connect()
            
            result = import_data(db, json_path, 'json')
            
            assert result['success'] is True
            
            db.disconnect()
        finally:
            shutil.rmtree(temp_dir)