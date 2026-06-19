from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class OrderStatus(Enum):
    """Статусы заказа"""
    NEW = 'новый'
    IN_DELIVERY = 'в доставке'
    COMPLETED = 'выполнен'
    CANCELLED = 'отменён'
    
    @classmethod
    def choices(cls):
        return [status.value for status in cls]


@dataclass
class Customer:
    """Клиент"""
    name: str
    phone: str = ''
    address: str = ''
    id: Optional[int] = None
    
    def __post_init__(self):
        if not self.name:
            raise ValueError("Имя клиента обязательно")
    
    def to_dict(self):
        """Преобразование в словарь"""
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'address': self.address
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Создание из словаря"""
        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            phone=data.get('phone', ''),
            address=data.get('address', '')
        )


@dataclass
class OrderItem:
    """Позиция заказа (товар)"""
    product_name: str
    quantity: int
    price: float
    id: Optional[int] = None
    order_id: Optional[int] = None
    
    def __post_init__(self):
        if not self.product_name:
            raise ValueError("Название товара обязательно")
        if self.quantity <= 0:
            raise ValueError("Количество должно быть больше 0")
        if self.price < 0:
            raise ValueError("Цена не может быть отрицательной")
    
    @property
    def total(self):
        """Стоимость позиции"""
        return self.quantity * self.price
    
    def to_dict(self):
        """Преобразование в словарь"""
        return {
            'id': self.id,
            'order_id': self.order_id,
            'product_name': self.product_name,
            'quantity': self.quantity,
            'price': self.price
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Создание из словаря"""
        return cls(
            id=data.get('id'),
            order_id=data.get('order_id'),
            product_name=data.get('product_name', ''),
            quantity=data.get('quantity', 0),
            price=data.get('price', 0.0)
        )


@dataclass
class Order:
    """Заказ"""
    customer_id: int
    order_date: str
    status: str = OrderStatus.NEW.value
    total: float = 0.0
    items: List[OrderItem] = field(default_factory=list)
    id: Optional[int] = None
    
    def __post_init__(self):
        if not self.customer_id:
            raise ValueError("ID клиента обязательно")
        if not self.order_date:
            raise ValueError("Дата заказа обязательна")
        if self.status not in OrderStatus.choices():
            raise ValueError(f"Неверный статус заказа. Допустимые: {OrderStatus.choices()}")
        
        # Пересчитываем общую сумму если не передана
        if self.total == 0.0 and self.items:
            self.total = sum(item.total for item in self.items)
    
    def add_item(self, item: OrderItem):
        """Добавить позицию в заказ"""
        item.order_id = self.id
        self.items.append(item)
        self.total = sum(i.total for i in self.items)
    
    def remove_item(self, item_id: int):
        """Удалить позицию из заказа"""
        self.items = [i for i in self.items if i.id != item_id]
        self.total = sum(i.total for i in self.items)
    
    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'order_date': self.order_date,
            'status': self.status,
            'total': self.total,
            'items': [item.to_dict() for item in self.items]
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Создание из словаря"""
        items = [OrderItem.from_dict(item) for item in data.get('items', [])]
        return cls(
            id=data.get('id'),
            customer_id=data.get('customer_id', 0),
            order_date=data.get('order_date', ''),
            status=data.get('status', OrderStatus.NEW.value),
            total=data.get('total', 0.0),
            items=items
        )