import pytest
from models import Customer, Order, OrderItem, OrderStatus


class TestCustomer:
    """Тесты для модели Customer"""
    
    def test_create_customer_success(self):
        """Успешное создание клиента"""
        customer = Customer(name="Иван Петров", phone="+79991234567", address="г. Москва, ул. Ленина, 1")
        
        assert customer.name == "Иван Петров"
        assert customer.phone == "+79991234567"
        assert customer.address == "г. Москва, ул. Ленина, 1"
        assert customer.id is None
    
    def test_create_customer_minimal(self):
        """Создание клиента только с именем"""
        customer = Customer(name="Петр")
        
        assert customer.name == "Петр"
        assert customer.phone == ""
        assert customer.address == ""
    
    def test_create_customer_without_name_raises_error(self):
        """Создание клиента без имени вызывает ошибку"""
        with pytest.raises(ValueError, match="Имя клиента обязательно"):
            Customer(name="")
    
    def test_customer_to_dict(self):
        """Преобразование клиента в словарь"""
        customer = Customer(
            id=1,
            name="Иван Петров",
            phone="+79991234567",
            address="г. Москва"
        )
        
        result = customer.to_dict()
        
        assert result == {
            'id': 1,
            'name': "Иван Петров",
            'phone': "+79991234567",
            'address': "г. Москва"
        }
    
    def test_customer_from_dict(self):
        """Создание клиента из словаря"""
        data = {
            'id': 1,
            'name': "Иван Петров",
            'phone': "+79991234567",
            'address': "г. Москва"
        }
        
        customer = Customer.from_dict(data)
        
        assert customer.id == 1
        assert customer.name == "Иван Петров"
        assert customer.phone == "+79991234567"
        assert customer.address == "г. Москва"


class TestOrderItem:
    """Тесты для модели OrderItem"""
    
    def test_create_order_item_success(self):
        """Успешное создание позиции заказа"""
        item = OrderItem(
            product_name="Пицца Маргарита",
            quantity=2,
            price=500.0
        )
        
        assert item.product_name == "Пицца Маргарита"
        assert item.quantity == 2
        assert item.price == 500.0
        assert item.total == 1000.0
    
    def test_order_item_total_calculation(self):
        """Расчет стоимости позиции"""
        item = OrderItem(product_name="Товар", quantity=3, price=100.0)
        assert item.total == 300.0
    
    def test_create_order_item_zero_quantity_raises_error(self):
        """Количество 0 вызывает ошибку"""
        with pytest.raises(ValueError, match="Количество должно быть больше 0"):
            OrderItem(product_name="Товар", quantity=0, price=100.0)
    
    def test_create_order_item_negative_quantity_raises_error(self):
        """Отрицательное количество вызывает ошибку"""
        with pytest.raises(ValueError, match="Количество должно быть больше 0"):
            OrderItem(product_name="Товар", quantity=-1, price=100.0)
    
    def test_create_order_item_negative_price_raises_error(self):
        """Отрицательная цена вызывает ошибку"""
        with pytest.raises(ValueError, match="Цена не может быть отрицательной"):
            OrderItem(product_name="Товар", quantity=1, price=-100.0)
    
    def test_create_order_item_without_name_raises_error(self):
        """Пустое название товара вызывает ошибку"""
        with pytest.raises(ValueError, match="Название товара обязательно"):
            OrderItem(product_name="", quantity=1, price=100.0)
    
    def test_order_item_to_dict(self):
        """Преобразование позиции в словарь"""
        item = OrderItem(
            id=1,
            order_id=10,
            product_name="Пицца",
            quantity=2,
            price=500.0
        )
        
        result = item.to_dict()
        
        assert result == {
            'id': 1,
            'order_id': 10,
            'product_name': "Пицца",
            'quantity': 2,
            'price': 500.0
        }
    
    def test_order_item_from_dict(self):
        """Создание позиции из словаря"""
        data = {
            'id': 1,
            'order_id': 10,
            'product_name': "Пицца",
            'quantity': 2,
            'price': 500.0
        }
        
        item = OrderItem.from_dict(data)
        
        assert item.id == 1
        assert item.order_id == 10
        assert item.product_name == "Пицца"
        assert item.quantity == 2
        assert item.price == 500.0


class TestOrder:
    """Тесты для модели Order"""
    
    def test_create_order_success(self):
        """Успешное создание заказа"""
        order = Order(
            customer_id=1,
            order_date="2025-06-17",
            status="новый"
        )
        
        assert order.customer_id == 1
        assert order.order_date == "2025-06-17"
        assert order.status == "новый"
        assert order.total == 0.0
    
    def test_create_order_with_items(self):
        """Создание заказа с позициями"""
        items = [
            OrderItem(product_name="Пицца", quantity=2, price=500.0),
            OrderItem(product_name="Суши", quantity=1, price=300.0)
        ]
        
        order = Order(
            customer_id=1,
            order_date="2025-06-17",
            items=items
        )
        
        assert len(order.items) == 2
        assert order.total == 1300.0  # 2*500 + 1*300
    
    def test_create_order_default_status(self):
        """Заказ создается со статусом 'новый' по умолчанию"""
        order = Order(customer_id=1, order_date="2025-06-17")
        assert order.status == OrderStatus.NEW.value
    
    def test_create_order_without_customer_id_raises_error(self):
        """Отсутствие customer_id вызывает ошибку"""
        with pytest.raises(ValueError, match="ID клиента обязательно"):
            Order(customer_id=0, order_date="2025-06-17")
    
    def test_create_order_without_date_raises_error(self):
        """Отсутствие даты вызывает ошибку"""
        with pytest.raises(ValueError, match="Дата заказа обязательна"):
            Order(customer_id=1, order_date="")
    
    def test_create_order_invalid_status_raises_error(self):
        """Неверный статус вызывает ошибку"""
        with pytest.raises(ValueError, match="Неверный статус заказа"):
            Order(customer_id=1, order_date="2025-06-17", status="неизвестный статус")
    
    def test_order_add_item(self):
        """Добавление позиции в заказ"""
        order = Order(customer_id=1, order_date="2025-06-17")
        item = OrderItem(product_name="Пицца", quantity=2, price=500.0)
        
        order.add_item(item)
        
        assert len(order.items) == 1
        assert order.items[0].product_name == "Пицца"
        assert order.total == 1000.0
    
    def test_order_remove_item(self):
        """Удаление позиции из заказа"""
        items = [
            OrderItem(id=1, product_name="Пицца", quantity=2, price=500.0),
            OrderItem(id=2, product_name="Суши", quantity=1, price=300.0)
        ]
        order = Order(customer_id=1, order_date="2025-06-17", items=items)
        
        order.remove_item(1)
        
        assert len(order.items) == 1
        assert order.items[0].product_name == "Суши"
        assert order.total == 300.0
    
    def test_order_to_dict(self):
        """Преобразование заказа в словарь"""
        items = [OrderItem(id=1, product_name="Пицца", quantity=2, price=500.0)]
        order = Order(
            id=10,
            customer_id=1,
            order_date="2025-06-17",
            status="в доставке",
            total=1000.0,
            items=items
        )
        
        result = order.to_dict()
        
        assert result['id'] == 10
        assert result['customer_id'] == 1
        assert result['order_date'] == "2025-06-17"
        assert result['status'] == "в доставке"
        assert result['total'] == 1000.0
        assert len(result['items']) == 1
    
    def test_order_from_dict(self):
        """Создание заказа из словаря"""
        data = {
            'id': 10,
            'customer_id': 1,
            'order_date': "2025-06-17",
            'status': "в доставке",
            'total': 1000.0,
            'items': [
                {'product_name': "Пицца", 'quantity': 2, 'price': 500.0}
            ]
        }
        
        order = Order.from_dict(data)
        
        assert order.id == 10
        assert order.customer_id == 1
        assert len(order.items) == 1
        assert order.items[0].product_name == "Пицца"


class TestOrderStatus:
    """Тесты для перечисления статусов"""
    
    def test_order_status_choices(self):
        """Получение списка всех статусов"""
        choices = OrderStatus.choices()
        
        assert len(choices) == 4
        assert 'новый' in choices
        assert 'в доставке' in choices
        assert 'выполнен' in choices
        assert 'отменён' in choices
    
    def test_order_status_values(self):
        """Проверка значений статусов"""
        assert OrderStatus.NEW.value == 'новый'
        assert OrderStatus.IN_DELIVERY.value == 'в доставке'
        assert OrderStatus.COMPLETED.value == 'выполнен'
        assert OrderStatus.CANCELLED.value == 'отменён'