import pytest
import subprocess
import sys
import os
import tempfile
import shutil
import json
from pathlib import Path


class TestCLIArguments:
    """Тесты аргументов командной строки"""
    
    def test_cli_no_command_shows_help(self):
        """Запуск без команды показывает справку"""
        result = subprocess.run(
            [sys.executable, 'main_cli.py'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert 'usage' in result.stdout.lower() or 'help' in result.stdout.lower()
    
    def test_cli_invalid_command(self):
        """Неверная команда вызывает ошибку"""
        result = subprocess.run(
            [sys.executable, 'main_cli.py', 'invalid_command'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode != 0
    
    def test_cli_report_requires_period(self):
        """Команда report требует аргумент --period"""
        result = subprocess.run(
            [sys.executable, 'main_cli.py', 'report'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode != 0
        assert '--period' in result.stderr or 'required' in result.stderr.lower()
    
    def test_cli_report_invalid_period(self):
        """Неверный период вызывает ошибку"""
        result = subprocess.run(
            [sys.executable, 'main_cli.py', 'report', '--period', 'invalid'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode != 0
    
    def test_cli_export_requires_file(self):
        """Команда export требует аргумент --file"""
        result = subprocess.run(
            [sys.executable, 'main_cli.py', 'export'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode != 0
    
    def test_cli_import_requires_file(self):
        """Команда import требует аргумент --file"""
        result = subprocess.run(
            [sys.executable, 'main_cli.py', 'import'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode != 0


class TestCLIReport:
    """Тесты команды report"""
    
    @pytest.fixture
    def temp_db_with_data(self):
        """Создание временной БД с данными"""
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, 'test.db')
        
        # Импортируем здесь для создания данных
        from database import SQLiteDatabase
        from models import Customer, Order, OrderItem
        from datetime import datetime, timedelta
        
        db = SQLiteDatabase(db_path)
        db.connect()
        
        # Создаем клиента
        customer = Customer(name="Тестовый клиент", phone="+79991234567")
        customer = db.create_customer(customer)
        
        # Создаем заказы
        today = datetime.now().date()
        for i in range(3):
            order_date = (today - timedelta(days=i)).isoformat()
            order = Order(
                customer_id=customer.id,
                order_date=order_date,
                status="новый" if i == 0 else "выполнен",
                items=[OrderItem(product_name=f"Товар {i}", quantity=1, price=100.0)]
            )
            db.create_order(order)
        
        yield db_path, temp_dir
        
        db.disconnect()
        shutil.rmtree(temp_dir)
    
    def test_cli_report_day(self, temp_db_with_data):
        """Отчёт за день"""
        db_path, temp_dir = temp_db_with_data
        
        result = subprocess.run(
            [sys.executable, 'main_cli.py', '--db', 'sqlite', '--db-path', db_path,
             'report', '--period', 'day'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)) or '.'
        )
        
        assert result.returncode == 0
        assert 'ОТЧЁТ' in result.stdout or 'отчёт' in result.stdout.lower()
    
    def test_cli_report_week(self, temp_db_with_data):
        """Отчёт за неделю"""
        db_path, temp_dir = temp_db_with_data
        
        result = subprocess.run(
            [sys.executable, 'main_cli.py', '--db', 'sqlite', '--db-path', db_path,
             'report', '--period', 'week'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)) or '.'
        )
        
        assert result.returncode == 0
        assert 'недел' in result.stdout.lower() or 'ОТЧЁТ' in result.stdout
    
    def test_cli_report_month(self, temp_db_with_data):
        """Отчёт за месяц"""
        db_path, temp_dir = temp_db_with_data
        
        result = subprocess.run(
            [sys.executable, 'main_cli.py', '--db', 'sqlite', '--db-path', db_path,
             'report', '--period', 'month'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)) or '.'
        )
        
        assert result.returncode == 0
        assert 'месяц' in result.stdout.lower() or 'ОТЧЁТ' in result.stdout


class TestCLIExport:
    """Тесты команды export"""
    
    def test_cli_export_json(self):
        """Экспорт в JSON через CLI"""
        temp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(temp_dir, 'test.db')
            output_file = os.path.join(temp_dir, 'export.json')
            
            # Создаем пустую БД
            from database import SQLiteDatabase
            db = SQLiteDatabase(db_path)
            db.connect()
            db.disconnect()
            
            result = subprocess.run(
                [sys.executable, 'main_cli.py', '--db', 'sqlite', '--db-path', db_path,
                 'export', '--file', output_file],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__)) or '.'
            )
            
            assert result.returncode == 0
            assert os.path.exists(output_file)
            
        finally:
            shutil.rmtree(temp_dir)
    
    def test_cli_export_xml(self):
        """Экспорт в XML через CLI"""
        temp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(temp_dir, 'test.db')
            output_file = os.path.join(temp_dir, 'export.xml')
            
            from database import SQLiteDatabase
            db = SQLiteDatabase(db_path)
            db.connect()
            db.disconnect()
            
            result = subprocess.run(
                [sys.executable, 'main_cli.py', '--db', 'sqlite', '--db-path', db_path,
                 'export', '--file', output_file],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__)) or '.'
            )
            
            assert result.returncode == 0
            assert os.path.exists(output_file)
            
        finally:
            shutil.rmtree(temp_dir)


class TestCLIImport:
    """Тесты команды import"""
    
    def test_cli_import_json(self):
        """Импорт из JSON через CLI"""
        temp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(temp_dir, 'test.db')
            import_file = os.path.join(temp_dir, 'import.json')
            
            # Создаем JSON файл
            data = {
                'customers': [
                    {'id': 1, 'name': 'Тест', 'phone': '+79991234567', 'address': 'Москва'}
                ],
                'orders': []
            }
            with open(import_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            
            # Создаем пустую БД
            from database import SQLiteDatabase
            db = SQLiteDatabase(db_path)
            db.connect()
            db.disconnect()
            
            result = subprocess.run(
                [sys.executable, 'main_cli.py', '--db', 'sqlite', '--db-path', db_path,
                 'import', '--file', import_file],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__)) or '.'
            )
            
            assert result.returncode == 0
            assert 'импорт' in result.stdout.lower() or 'успеш' in result.stdout.lower()
            
        finally:
            shutil.rmtree(temp_dir)
    
    def test_cli_import_file_not_found(self):
        """Импорт несуществующего файла"""
        temp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(temp_dir, 'test.db')
            
            from database import SQLiteDatabase
            db = SQLiteDatabase(db_path)
            db.connect()
            db.disconnect()
            
            result = subprocess.run(
                [sys.executable, 'main_cli.py', '--db', 'sqlite', '--db-path', db_path,
                 'import', '--file', '/nonexistent/file.json'],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__)) or '.'
            )
            
            assert result.returncode != 0
            
        finally:
            shutil.rmtree(temp_dir)


class TestCLIDatabaseTypes:
    """Тесты работы с разными типами БД"""
    
    def test_cli_with_sqlite(self):
        """Работа с SQLite"""
        temp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(temp_dir, 'test.db')
            
            result = subprocess.run(
                [sys.executable, 'main_cli.py', '--db', 'sqlite', '--db-path', db_path,
                 'report', '--period', 'month'],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__)) or '.'
            )
            
            assert result.returncode == 0
            
        finally:
            shutil.rmtree(temp_dir)
    
    def test_cli_with_tinydb(self):
        """Работа с TinyDB"""
        temp_dir = tempfile.mkdtemp()
        try:
            db_path = os.path.join(temp_dir, 'test.json')
            
            result = subprocess.run(
                [sys.executable, 'main_cli.py', '--db', 'tinydb', '--db-path', db_path,
                 'report', '--period', 'month'],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.abspath(__file__)) or '.'
            )
            
            assert result.returncode == 0
            
        finally:
            shutil.rmtree(temp_dir)