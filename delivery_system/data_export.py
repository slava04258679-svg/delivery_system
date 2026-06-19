import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import List, Dict, Any
from datetime import datetime
import os

from models import Customer, Order, OrderItem, OrderStatus
from database import DatabaseInterface
from logger_config import logger


class DataExporter:
    """Класс для экспорта данных"""
    
    def __init__(self, db: DatabaseInterface):
        self.db = db
    
    def export_to_json(self, filepath: str) -> bool:
        """
        Экспорт всех заказов в JSON
        
        Args:
            filepath: Путь к файлу для сохранения
        
        Returns:
            True если экспорт успешен
        """
        try:
            orders = self.db.get_all_orders()
            customers = {c.id: c for c in self.db.get_all_customers()}
            
            data = {
                'export_date': datetime.now().isoformat(),
                'customers': [],
                'orders': []
            }
            
            # Экспортируем клиентов (только тех, у кого есть заказы)
            customer_ids = set()
            for order in orders:
                customer_ids.add(order.customer_id)
            
            for customer_id in customer_ids:
                if customer_id in customers:
                    data['customers'].append(customers[customer_id].to_dict())
            
            # Экспортируем заказы
            for order in orders:
                order_data = order.to_dict()
                data['orders'].append(order_data)
            
            # Создаем директорию если нужно
            dir_path = os.path.dirname(filepath)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)
            
            # Сохраняем в файл
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Экспорт в JSON выполнен: {filepath} ({len(orders)} заказов)")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка экспорта в JSON: {e}")
            return False
    
    def export_to_xml(self, filepath: str) -> bool:
        """
        Экспорт всех заказов в XML
        
        Args:
            filepath: Путь к файлу для сохранения
        
        Returns:
            True если экспорт успешен
        """
        try:
            orders = self.db.get_all_orders()
            customers = {c.id: c for c in self.db.get_all_customers()}
            
            # Создаем корневой элемент
            root = ET.Element('delivery_data')
            root.set('export_date', datetime.now().isoformat())
            
            # Добавляем клиентов
            customers_elem = ET.SubElement(root, 'customers')
            customer_ids = set()
            
            for order in orders:
                customer_ids.add(order.customer_id)
            
            for customer_id in customer_ids:
                if customer_id in customers:
                    customer = customers[customer_id]
                    customer_elem = ET.SubElement(customers_elem, 'customer')
                    customer_elem.set('id', str(customer.id))
                    
                    name_elem = ET.SubElement(customer_elem, 'name')
                    name_elem.text = customer.name
                    
                    phone_elem = ET.SubElement(customer_elem, 'phone')
                    phone_elem.text = customer.phone or ''
                    
                    address_elem = ET.SubElement(customer_elem, 'address')
                    address_elem.text = customer.address or ''
            
            # Добавляем заказы
            orders_elem = ET.SubElement(root, 'orders')
            
            for order in orders:
                order_elem = ET.SubElement(orders_elem, 'order')
                order_elem.set('id', str(order.id))
                
                customer_id_elem = ET.SubElement(order_elem, 'customer_id')
                customer_id_elem.text = str(order.customer_id)
                
                order_date_elem = ET.SubElement(order_elem, 'order_date')
                order_date_elem.text = order.order_date
                
                status_elem = ET.SubElement(order_elem, 'status')
                status_elem.text = order.status
                
                total_elem = ET.SubElement(order_elem, 'total')
                total_elem.text = str(order.total)
                
                # Добавляем позиции заказа
                items_elem = ET.SubElement(order_elem, 'items')
                for item in order.items:
                    item_elem = ET.SubElement(items_elem, 'item')
                    
                    product_name = ET.SubElement(item_elem, 'product_name')
                    product_name.text = item.product_name
                    
                    quantity = ET.SubElement(item_elem, 'quantity')
                    quantity.text = str(item.quantity)
                    
                    price = ET.SubElement(item_elem, 'price')
                    price.text = str(item.price)
            
            # Форматируем XML
            xml_str = ET.tostring(root, encoding='unicode')
            parsed = minidom.parseString(xml_str)
            pretty_xml = parsed.toprettyxml(indent="  ", encoding=None)
            
            # Убираем лишние пустые строки
            lines = pretty_xml.split('\n')
            pretty_xml = '\n'.join([line for line in lines if line.strip()])
            
            # Создаем директорию если нужно
            dir_path = os.path.dirname(filepath)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)
            
            # Сохраняем в файл
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(pretty_xml)
            
            logger.info(f"Экспорт в XML выполнен: {filepath} ({len(orders)} заказов)")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка экспорта в XML: {e}")
            return False


class DataImporter:
    """Класс для импорта данных"""
    
    def __init__(self, db: DatabaseInterface):
        self.db = db
        self.imported_customers = {}  # old_id -> new_id
        self.imported_orders = {}     # old_id -> new_id
    
    def import_from_json(self, filepath: str, skip_existing: bool = True) -> Dict[str, Any]:
        """
        Импорт заказов из JSON
        
        Args:
            filepath: Путь к файлу для импорта
            skip_existing: Пропускать существующие заказы
        
        Returns:
            Словарь с результатами импорта
        """
        result = {
            'success': False,
            'customers_imported': 0,
            'orders_imported': 0,
            'orders_skipped': 0,
            'errors': []
        }
        
        try:
            # Проверяем существование файла
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Файл не найден: {filepath}")
            
            # Читаем файл
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Валидируем структуру
            if not self._validate_json_structure(data):
                raise ValueError("Неверная структура JSON файла")
            
            self.imported_customers = {}
            self.imported_orders = {}
            
            # Импортируем клиентов
            if 'customers' in data:
                for customer_data in data['customers']:
                    try:
                        old_id = customer_data.get('id')
                        customer = Customer.from_dict(customer_data)
                        customer.id = None  # Сбрасываем ID для создания нового
                        
                        # Проверяем существует ли клиент с таким же именем и телефоном
                        existing = self._find_existing_customer(customer)
                        if existing:
                            self.imported_customers[old_id] = existing.id
                        else:
                            new_customer = self.db.create_customer(customer)
                            self.imported_customers[old_id] = new_customer.id
                            result['customers_imported'] += 1
                            
                    except Exception as e:
                        result['errors'].append(f"Ошибка импорта клиента {customer_data.get('id')}: {e}")
            
            # Импортируем заказы
            if 'orders' in data:
                for order_data in data['orders']:
                    try:
                        old_order_id = order_data.get('id')
                        
                        # Проверяем существует ли заказ
                        existing_order = self.db.get_order(old_order_id) if 'id' in order_data else None
                        if existing_order and skip_existing:
                            result['orders_skipped'] += 1
                            continue
                        
                        # Создаем заказ
                        order = Order.from_dict(order_data)
                        order.id = None  # Сбрасываем ID
                        
                        # Обновляем customer_id на новый
                        if order.customer_id in self.imported_customers:
                            order.customer_id = self.imported_customers[order.customer_id]
                        
                        # Сбрасываем ID у элементов
                        for item in order.items:
                            item.id = None
                            item.order_id = None
                        
                        new_order = self.db.create_order(order)
                        self.imported_orders[old_order_id] = new_order.id
                        result['orders_imported'] += 1
                        
                    except Exception as e:
                        result['errors'].append(f"Ошибка импорта заказа {order_data.get('id')}: {e}")
            
            result['success'] = True
            logger.info(
                f"Импорт из JSON завершен: "
                f"{result['customers_imported']} клиентов, "
                f"{result['orders_imported']} заказов, "
                f"{result['orders_skipped']} пропущено"
            )
            
        except Exception as e:
            result['errors'].append(str(e))
            logger.error(f"Ошибка импорта из JSON: {e}")
        
        return result
    
    def import_from_xml(self, filepath: str, skip_existing: bool = True) -> Dict[str, Any]:
        """
        Импорт заказов из XML
        
        Args:
            filepath: Путь к файлу для импорта
            skip_existing: Пропускать существующие заказы
        
        Returns:
            Словарь с результатами импорта
        """
        result = {
            'success': False,
            'customers_imported': 0,
            'orders_imported': 0,
            'orders_skipped': 0,
            'errors': []
        }
        
        try:
            # Проверяем существование файла
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Файл не найден: {filepath}")
            
            # Парсим XML
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            # Валидируем структуру
            if root.tag != 'delivery_data':
                raise ValueError("Неверная структура XML файла: ожидается 'delivery_data'")
            
            self.imported_customers = {}
            self.imported_orders = {}
            
            # Импортируем клиентов
            customers_elem = root.find('customers')
            if customers_elem is not None:
                for customer_elem in customers_elem.findall('customer'):
                    try:
                        old_id = int(customer_elem.get('id'))
                        
                        name_elem = customer_elem.find('name')
                        phone_elem = customer_elem.find('phone')
                        address_elem = customer_elem.find('address')
                        
                        customer = Customer(
                            name=name_elem.text if name_elem is not None and name_elem.text else '',
                            phone=phone_elem.text if phone_elem is not None else '',
                            address=address_elem.text if address_elem is not None else ''
                        )
                        
                        # Проверяем существует ли клиент
                        existing = self._find_existing_customer(customer)
                        if existing:
                            self.imported_customers[old_id] = existing.id
                        else:
                            new_customer = self.db.create_customer(customer)
                            self.imported_customers[old_id] = new_customer.id
                            result['customers_imported'] += 1
                            
                    except Exception as e:
                        result['errors'].append(f"Ошибка импорта клиента {old_id}: {e}")
            
            # Импортируем заказы
            orders_elem = root.find('orders')
            if orders_elem is not None:
                for order_elem in orders_elem.findall('order'):
                    try:
                        old_order_id = int(order_elem.get('id'))
                        
                        # Проверяем существует ли заказ
                        existing_order = self.db.get_order(old_order_id)
                        if existing_order and skip_existing:
                            result['orders_skipped'] += 1
                            continue
                        
                        # Читаем данные заказа
                        customer_id_elem = order_elem.find('customer_id')
                        order_date_elem = order_elem.find('order_date')
                        status_elem = order_elem.find('status')
                        total_elem = order_elem.find('total')
                        
                        customer_id = int(customer_id_elem.text) if customer_id_elem is not None and customer_id_elem.text else 0
                        order_date = order_date_elem.text if order_date_elem is not None and order_date_elem.text else ''
                        status = status_elem.text if status_elem is not None and status_elem.text else OrderStatus.NEW.value
                        total = float(total_elem.text) if total_elem is not None and total_elem.text else 0.0
                        
                        # Обновляем customer_id на новый
                        new_customer_id = self.imported_customers.get(customer_id, customer_id)
                        
                        # Читаем позиции заказа
                        items = []
                        items_elem = order_elem.find('items')
                        if items_elem is not None:
                            for item_elem in items_elem.findall('item'):
                                product_name_elem = item_elem.find('product_name')
                                quantity_elem = item_elem.find('quantity')
                                price_elem = item_elem.find('price')
                                
                                item = OrderItem(
                                    product_name=product_name_elem.text if product_name_elem is not None and product_name_elem.text else '',
                                    quantity=int(quantity_elem.text) if quantity_elem is not None and quantity_elem.text else 0,
                                    price=float(price_elem.text) if price_elem is not None and price_elem.text else 0.0
                                )
                                items.append(item)
                        
                        # Создаем заказ
                        order = Order(
                            customer_id=new_customer_id,
                            order_date=order_date,
                            status=status,
                            total=total,
                            items=items
                        )
                        
                        new_order = self.db.create_order(order)
                        self.imported_orders[old_order_id] = new_order.id
                        result['orders_imported'] += 1
                        
                    except Exception as e:
                        result['errors'].append(f"Ошибка импорта заказа {old_order_id}: {e}")
            
            result['success'] = True
            logger.info(
                f"Импорт из XML завершен: "
                f"{result['customers_imported']} клиентов, "
                f"{result['orders_imported']} заказов, "
                f"{result['orders_skipped']} пропущено"
            )
            
        except Exception as e:
            result['errors'].append(str(e))
            logger.error(f"Ошибка импорта из XML: {e}")
        
        return result
    
    def _validate_json_structure(self, data: Dict) -> bool:
        """Проверка структуры JSON данных"""
        if not isinstance(data, dict):
            return False
        
        # Должен быть хотя бы orders или customers
        if 'orders' not in data and 'customers' not in data:
            return False
        
        # Проверяем orders если есть
        if 'orders' in data and not isinstance(data['orders'], list):
            return False
        
        # Проверяем customers если есть
        if 'customers' in data and not isinstance(data['customers'], list):
            return False
        
        return True
    
    def _find_existing_customer(self, customer: Customer) -> Customer:
        """
        Поиск существующего клиента по имени и телефону
        
        Args:
            customer: Клиент для поиска
        
        Returns:
            Найденный клиент или None
        """
        all_customers = self.db.get_all_customers()
        
        for existing in all_customers:
            if (existing.name == customer.name and 
                existing.phone == customer.phone):
                return existing
        
        return None


def export_data(db: DatabaseInterface, filepath: str, format: str = 'json') -> bool:
    """
    Удобная функция для экспорта данных
    
    Args:
        db: Экземпляр базы данных
        filepath: Путь к файлу
        format: 'json' или 'xml'
    
    Returns:
        True если экспорт успешен
    """
    exporter = DataExporter(db)
    
    if format.lower() == 'json':
        return exporter.export_to_json(filepath)
    elif format.lower() == 'xml':
        return exporter.export_to_xml(filepath)
    else:
        logger.error(f"Неподдерживаемый формат экспорта: {format}")
        return False


def import_data(db: DatabaseInterface, filepath: str, format: str = 'json', skip_existing: bool = True) -> Dict[str, Any]:
    """
    Удобная функция для импорта данных
    
    Args:
        db: Экземпляр базы данных
        filepath: Путь к файлу
        format: 'json' или 'xml'
        skip_existing: Пропускать существующие заказы
    
    Returns:
        Словарь с результатами импорта
    """
    importer = DataImporter(db)
    
    if format.lower() == 'json':
        return importer.import_from_json(filepath, skip_existing)
    elif format.lower() == 'xml':
        return importer.import_from_xml(filepath, skip_existing)
    else:
        logger.error(f"Неподдерживаемый формат импорта: {format}")
        return {
            'success': False,
            'errors': [f"Неподдерживаемый формат: {format}"]
        }