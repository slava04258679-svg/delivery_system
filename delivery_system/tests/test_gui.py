import pytest
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestGUIImports:
    """Тесты импорта GUI модулей"""
    
    def test_import_main_gui(self):
        """Импорт main_gui модуля"""
        try:
            import main_gui
            assert hasattr(main_gui, 'MainApplication')
            assert hasattr(main_gui, 'OrderDialog')
            assert hasattr(main_gui, 'ReportDialog')
        except ImportError as e:
            pytest.skip(f"Не удалось импортировать main_gui: {e}")
    
    def test_import_tkinter(self):
        """Импорт tkinter"""
        try:
            import tkinter as tk
            assert tk is not None
        except ImportError as e:
            pytest.skip(f"Tkinter не установлен: {e}")


class TestGUIClasses:
    """Тесты классов GUI"""
    
    def test_main_application_class_exists(self):
        """Проверка существования класса MainApplication"""
        try:
            from main_gui import MainApplication
            assert MainApplication is not None
        except ImportError:
            pytest.skip("Не удалось импортировать MainApplication")
    
    def test_order_dialog_class_exists(self):
        """Проверка существования класса OrderDialog"""
        try:
            from main_gui import OrderDialog
            assert OrderDialog is not None
        except ImportError:
            pytest.skip("Не удалось импортировать OrderDialog")
    
    def test_report_dialog_class_exists(self):
        """Проверка существования класса ReportDialog"""
        try:
            from main_gui import ReportDialog
            assert ReportDialog is not None
        except ImportError:
            pytest.skip("Не удалось импортировать ReportDialog")


class TestGUIFunctionality:
    """Тесты функциональности GUI (без запуска)"""
    
    def test_database_connection_in_gui(self):
        """Тест подключения к БД в GUI контексте"""
        import tempfile
        import shutil
        from database import SQLiteDatabase
        from models import Customer, Order
        
        temp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(temp_dir, 'test.db')
            db = SQLiteDatabase(db_path)
            db.connect()
            
            # Создаем тестовые данные
            customer = Customer(name="Тестовый клиент")
            customer = db.create_customer(customer)
            
            order = Order(customer_id=customer.id, order_date="2025-06-17")
            db.create_order(order)
            
            # Проверяем что данные созданы
            orders = db.get_all_orders()
            assert len(orders) == 1
            
            db.disconnect()
        finally:
            shutil.rmtree(temp_dir)
    
    def test_export_import_in_gui_context(self):
        """Тест экспорта/импорта в контексте GUI"""
        import tempfile
        import shutil
        import json
        from database import SQLiteDatabase
        from models import Customer, Order, OrderItem
        from data_export import DataExporter, DataImporter
        
        temp_dir = tempfile.mkdtemp()
        try:
            # Создаем БД с данными
            db_path = os.path.join(temp_dir, 'test.db')
            db = SQLiteDatabase(db_path)
            db.connect()
            
            customer = Customer(name="Тест")
            customer = db.create_customer(customer)
            
            items = [OrderItem(product_name="Товар", quantity=1, price=100.0)]
            order = Order(customer_id=customer.id, order_date="2025-06-17", items=items)
            db.create_order(order)
            
            # Экспорт
            json_path = os.path.join(temp_dir, 'export.json')
            exporter = DataExporter(db)
            assert exporter.export_to_json(json_path) is True
            
            # Импорт в новую БД
            db_path2 = os.path.join(temp_dir, 'test2.db')
            db2 = SQLiteDatabase(db_path2)
            db2.connect()
            
            importer = DataImporter(db2)
            result = importer.import_from_json(json_path)
            
            assert result['success'] is True
            assert result['orders_imported'] == 1
            
            db.disconnect()
            db2.disconnect()
        finally:
            shutil.rmtree(temp_dir)