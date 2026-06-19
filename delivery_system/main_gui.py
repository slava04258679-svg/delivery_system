import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime
from typing import Optional
import os

from database import DatabaseFactory, SQLiteDatabase, TinyDBDatabase
from models import Customer, Order, OrderItem, OrderStatus
from data_export import DataExporter, DataImporter
from logger_config import logger, setup_logger


class CustomerDialog(tk.Toplevel):
    
    def __init__(self, parent, db, customer: Optional[Customer] = None):
        super().__init__(parent)
        self.db = db
        self.customer = customer
        self.result = None
        
        self.title("Редактирование клиента" if customer else "Новый клиент")
        self.geometry("400x250")
        self.resizable(False, False)
        
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        self._load_data()
        
        self.wait_window()
    
    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Имя:*").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.name_var, width=40).grid(row=0, column=1, pady=5, padx=5)
        
        ttk.Label(main_frame, text="Телефон:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.phone_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.phone_var, width=40).grid(row=1, column=1, pady=5, padx=5)
        
        ttk.Label(main_frame, text="Адрес:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.address_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.address_var, width=40).grid(row=2, column=1, pady=5, padx=5)
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="OK", command=self._on_ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Отмена", command=self._on_cancel).pack(side=tk.LEFT, padx=10)
    
    def _load_data(self):
        """Загрузка данных клиента"""
        if self.customer:
            self.name_var.set(self.customer.name)
            self.phone_var.set(self.customer.phone or '')
            self.address_var.set(self.customer.address or '')
    
    def _on_ok(self):
        """Обработка нажатия OK"""
        if not self.name_var.get().strip():
            messagebox.showerror("Ошибка", "Имя клиента обязательно", parent=self)
            return
        
        self.result = Customer(
            name=self.name_var.get().strip(),
            phone=self.phone_var.get().strip(),
            address=self.address_var.get().strip()
        )
        self.destroy()
    
    def _on_cancel(self):
        """Отмена"""
        self.destroy()


class OrderDialog(tk.Toplevel):
    """Диалоговое окно для добавления/редактирования заказа"""
    
    def __init__(self, parent, db, order: Optional[Order] = None):
        super().__init__(parent)
        self.db = db
        self.order = order
        self.result = None
        
        self.title("Редактирование заказа" if order else "Новый заказ")
        self.geometry("600x500")
        self.resizable(True, True)
        
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        self._load_data()
        
        self.wait_window()
    
    def _create_widgets(self):
        """Создание виджетов"""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Клиент
        ttk.Label(main_frame, text="Клиент:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.customer_var = tk.StringVar()
        customers = self.db.get_all_customers()
        self.customer_combo = ttk.Combobox(
            main_frame,
            textvariable=self.customer_var,
            values=[f"{c.id}: {c.name}" for c in customers],
            state="readonly",
            width=40
        )
        self.customer_combo.grid(row=0, column=1, pady=5, padx=5)
        
        # Кнопка добавления клиента
        ttk.Button(main_frame, text="+", command=self._add_customer).grid(row=0, column=2, pady=5, padx=5)
        
        # Дата
        ttk.Label(main_frame, text="Дата:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(main_frame, textvariable=self.date_var, width=42).grid(row=1, column=1, pady=5, padx=5)
        
        # Статус
        ttk.Label(main_frame, text="Статус:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.status_var = tk.StringVar(value=OrderStatus.NEW.value)
        ttk.Combobox(
            main_frame,
            textvariable=self.status_var,
            values=OrderStatus.choices(),
            state="readonly",
            width=39
        ).grid(row=2, column=1, pady=5, padx=5)
        
        # Позиции заказа
        ttk.Label(main_frame, text="Позиции заказа:").grid(row=3, column=0, sticky=tk.W, pady=10)
        
        # TreeView для позиций
        items_frame = ttk.Frame(main_frame)
        items_frame.grid(row=4, column=0, columnspan=3, sticky=tk.NSEW, pady=5)
        
        self.items_tree = ttk.Treeview(
            items_frame,
            columns=("product", "quantity", "price"),
            show="headings",
            height=8
        )
        self.items_tree.heading("product", text="Товар")
        self.items_tree.heading("quantity", text="Количество")
        self.items_tree.heading("price", text="Цена")
        
        self.items_tree.column("product", width=200)
        self.items_tree.column("quantity", width=100)
        self.items_tree.column("price", width=100)
        
        scrollbar = ttk.Scrollbar(items_frame, orient=tk.VERTICAL, command=self.items_tree.yview)
        self.items_tree.configure(yscrollcommand=scrollbar.set)
        
        self.items_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Кнопки управления позициями
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=5, column=0, columnspan=3, pady=5)
        
        ttk.Button(btn_frame, text="Добавить позицию", command=self._add_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Удалить позицию", command=self._remove_item).pack(side=tk.LEFT, padx=5)
        
        # Итого
        self.total_var = tk.StringVar(value="0.00")
        ttk.Label(main_frame, text="Итого:").grid(row=6, column=0, sticky=tk.E, pady=10)
        ttk.Label(main_frame, textvariable=self.total_var, font=("Arial", 12, "bold")).grid(row=6, column=1, sticky=tk.W, pady=10, padx=5)
        
        # Кнопки OK/Cancel
        ok_cancel_frame = ttk.Frame(main_frame)
        ok_cancel_frame.grid(row=7, column=0, columnspan=3, pady=20)
        
        ttk.Button(ok_cancel_frame, text="OK", command=self._on_ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(ok_cancel_frame, text="Отмена", command=self._on_cancel).pack(side=tk.LEFT, padx=10)
        
        # Настройка весов для растягивания
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
    
    def _add_customer(self):
        """Добавление клиента прямо из диалога заказа"""
        dialog = CustomerDialog(self, self.db)
        if dialog.result:
            try:
                new_customer = self.db.create_customer(dialog.result)
                # Обновляем список клиентов в комбобоксе
                customers = self.db.get_all_customers()
                self.customer_combo['values'] = [f"{c.id}: {c.name}" for c in customers]
                # Выбираем нового клиента
                self.customer_var.set(f"{new_customer.id}: {new_customer.name}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось добавить клиента:\n{e}", parent=self)
    
    def _load_data(self):
        """Загрузка данных заказа"""
        if self.order:
            logger.debug(f"Загрузка заказа ID={self.order.id}")
            logger.debug(f"Позиций в заказе: {len(self.order.items)}")
            
            # Устанавливаем клиента
            customers = self.db.get_all_customers()
            for c in customers:
                if c.id == self.order.customer_id:
                    self.customer_var.set(f"{c.id}: {c.name}")
                    break
            
            # Устанавливаем дату и статус
            self.date_var.set(self.order.order_date)
            self.status_var.set(self.order.status)
            
            # Очищаем TreeView перед загрузкой
            for item in self.items_tree.get_children():
                self.items_tree.delete(item)
            
            # Загружаем позиции
            if self.order.items:
                for item in self.order.items:
                    logger.debug(f"Добавляем позицию: {item.product_name}, {item.quantity}, {item.price}")
                    self.items_tree.insert("", "end", values=(
                        item.product_name, 
                        item.quantity, 
                        item.price
                    ))
            else:
                logger.warning(f"Заказ {self.order.id} не имеет позиций!")
            
            # Обновляем итого
            self._update_total()
            logger.debug(f"Загружено позиций в TreeView: {len(self.items_tree.get_children())}")
    
    def _add_item(self):
        """Добавление позиции"""
        # Простой диалог для добавления позиции
        product = simpledialog.askstring("Товар", "Название товара:", parent=self)
        if not product:
            return
        
        quantity = simpledialog.askinteger("Количество", "Количество:", parent=self, minvalue=1)
        if not quantity:
            return
        
        price = simpledialog.askfloat("Цена", "Цена за единицу:", parent=self, minvalue=0.0)
        if price is None:
            return
        
        self.items_tree.insert("", "end", values=(product, quantity, price))
        self._update_total()
    
    def _remove_item(self):
        """Удаление позиции"""
        selection = self.items_tree.selection()
        if selection:
            self.items_tree.delete(selection)
            self._update_total()
    
    def _update_total(self):
        """Обновление итоговой суммы"""
        total = 0.0
        for item in self.items_tree.get_children():
            values = self.items_tree.item(item)["values"]
            if len(values) == 3:
                quantity = int(values[1])
                price = float(values[2])
                total += quantity * price
        
        self.total_var.set(f"{total:.2f}")
    
    def _on_ok(self):
        """Обработка нажатия OK"""
        # Валидация
        if not self.customer_var.get():
            messagebox.showerror("Ошибка", "Выберите клиента", parent=self)
            return
        
        if not self.date_var.get():
            messagebox.showerror("Ошибка", "Укажите дату", parent=self)
            return
        
        # Парсим customer_id
        try:
            customer_id = int(self.customer_var.get().split(":")[0])
        except (ValueError, IndexError):
            messagebox.showerror("Ошибка", "Неверный клиент", parent=self)
            return
        
        # Создаём позиции
        items = []
        for item in self.items_tree.get_children():
            values = self.items_tree.item(item)["values"]
            if len(values) == 3:
                items.append(OrderItem(
                    product_name=values[0],
                    quantity=int(values[1]),
                    price=float(values[2])
                ))
        
        # Создаём заказ
        self.result = Order(
            customer_id=customer_id,
            order_date=self.date_var.get(),
            status=self.status_var.get(),
            items=items
        )
        
        self.destroy()
    
    def _on_cancel(self):
        """Обработка нажатия Отмена"""
        self.destroy()


class CustomerManagementDialog(tk.Toplevel):
    """Окно управления клиентами"""
    
    def __init__(self, parent, db):
        super().__init__(parent)
        self.db = db
        
        self.title("Управление клиентами")
        self.geometry("600x400")
        self.resizable(True, True)
        
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        self._load_customers()
        
        self.wait_window()
    
    def _create_widgets(self):
        """Создание виджетов"""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # TreeView для клиентов
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("id", "name", "phone", "address"),
            show="headings"
        )
        
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Имя")
        self.tree.heading("phone", text="Телефон")
        self.tree.heading("address", text="Адрес")
        
        self.tree.column("id", width=50)
        self.tree.column("name", width=200)
        self.tree.column("phone", width=150)
        self.tree.column("address", width=200)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Кнопки
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(btn_frame, text="Добавить", command=self._add_customer).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Редактировать", command=self._edit_customer).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Удалить", command=self._delete_customer).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Двойной клик для редактирования
        self.tree.bind("<Double-1>", lambda e: self._edit_customer())
    
    def _load_customers(self):
        """Загрузка клиентов"""
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        customers = self.db.get_all_customers()
        for customer in customers:
            self.tree.insert("", "end", values=(
                customer.id,
                customer.name,
                customer.phone or '',
                customer.address or ''
            ))
    
    def _add_customer(self):
        """Добавление клиента"""
        dialog = CustomerDialog(self, self.db)
        if dialog.result:
            try:
                self.db.create_customer(dialog.result)
                self._load_customers()
                messagebox.showinfo("Успех", "Клиент успешно добавлен")
                logger.info(f"Создан клиент через GUI: {dialog.result.name}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось добавить клиента:\n{e}")
                logger.error(f"Ошибка создания клиента: {e}")
    
    def _edit_customer(self):
        """Редактирование клиента"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите клиента для редактирования")
            return
        
        item = self.tree.item(selection[0])
        customer_id = item["values"][0]
        
        customer = self.db.get_customer(customer_id)
        if not customer:
            messagebox.showerror("Ошибка", "Клиент не найден")
            return
        
        dialog = CustomerDialog(self, self.db, customer)
        if dialog.result:
            try:
                dialog.result.id = customer_id
                self.db.update_customer(dialog.result)
                self._load_customers()
                messagebox.showinfo("Успех", "Клиент успешно обновлён")
                logger.info(f"Обновлён клиент {customer_id} через GUI")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось обновить клиента:\n{e}")
                logger.error(f"Ошибка обновления клиента {customer_id}: {e}")
    
    def _delete_customer(self):
        """Удаление клиента"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите клиента для удаления")
            return
        
        item = self.tree.item(selection[0])
        customer_id = item["values"][0]
        
        if messagebox.askyesno("Подтверждение", f"Удалить клиента #{customer_id}?"):
            try:
                result = self.db.delete_customer(customer_id)
                if result:
                    self._load_customers()
                    messagebox.showinfo("Успех", "Клиент удалён")
                    logger.info(f"Удалён клиент {customer_id} через GUI")
                else:
                    messagebox.showwarning("Внимание", "Нельзя удалить клиента с активными заказами")
                    logger.warning(f"Попытка удаления клиента {customer_id} с заказами")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить клиента:\n{e}")
                logger.error(f"Ошибка удаления клиента {customer_id}: {e}")


class ReportDialog(tk.Toplevel):
    """Диалоговое окно для отображения отчёта"""
    
    def __init__(self, parent, db, period: str = "month"):
        super().__init__(parent)
        self.db = db
        
        self.title(f"Отчёт за {period}")
        self.geometry("500x400")
        self.resizable(True, True)
        
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        self._load_report(period)
        
        self.wait_window()
    
    def _create_widgets(self):
        """Создание виджетов"""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Текстовое поле для отчёта
        self.report_text = tk.Text(main_frame, wrap=tk.WORD, font=("Courier", 10))
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.report_text.yview)
        self.report_text.configure(yscrollcommand=scrollbar.set)
        
        self.report_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Кнопка закрытия
        ttk.Button(main_frame, text="Закрыть", command=self.destroy).pack(pady=10)
    
    def _load_report(self, period: str):
        """Загрузка данных отчёта"""
        from datetime import timedelta
        
        today = datetime.now().date()
        
        if period == 'day':
            start_date = today
            end_date = today
            period_name = "сегодня"
        elif period == 'week':
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
            period_name = "эту неделю"
        else:  # month
            start_date = today.replace(day=1)
            if today.month == 12:
                end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
            period_name = "этот месяц"
        
        # Получаем ВСЕ заказы за период
        all_orders = self.db.get_orders_by_date_range(start_date.isoformat(), end_date.isoformat())
        
        report = f"ОТЧЁТ ЗА {period_name.upper()}\n"
        report += f"Период: {start_date} - {end_date}\n"
        report += "=" * 50 + "\n\n"
        
        if not all_orders:
            report += "Заказов за указанный период не найдено.\n"
        else:
            # 1. Статусы (показываем ВСЕ заказы)
            report += "1. КОЛИЧЕСТВО ЗАКАЗОВ ПО СТАТУСАМ:\n"
            report += "-" * 40 + "\n"
            status_counts = {}
            for order in all_orders:
                status_counts[order.status] = status_counts.get(order.status, 0) + 1
            
            for status, count in sorted(status_counts.items()):
                report += f"  {status}: {count}\n"
            report += f"  Итого: {len(all_orders)}\n\n"
            
            # Фильтруем для финансовых расчётов
            active_orders = [o for o in all_orders if o.status != OrderStatus.CANCELLED.value]
            completed_orders = [o for o in all_orders if o.status == OrderStatus.COMPLETED.value]
            
            # 2. Топ-3 клиента (только активные заказы)
            report += "2. ТОП-3 КЛИЕНТА ПО СУММЕ ЗАКАЗОВ:\n"
            report += "   (только выполненные и в доставке)\n"
            report += "-" * 40 + "\n"
            
            customers = {c.id: c for c in self.db.get_all_customers()}
            customer_totals = {}
            
            for order in active_orders:
                if order.customer_id not in customer_totals:
                    customer_totals[order.customer_id] = 0
                customer_totals[order.customer_id] += order.total
            
            sorted_customers = sorted(customer_totals.items(), key=lambda x: x[1], reverse=True)[:3]
            
            if sorted_customers:
                for i, (customer_id, total) in enumerate(sorted_customers, 1):
                    customer = customers.get(customer_id)
                    if customer:
                        report += f"  {i}. {customer.name} - {total:.2f} руб.\n"
            else:
                report += "  Нет активных заказов\n"
            
            report += "\n"
            
            # 3. Общая выручка (ТОЛЬКО выполненные)
            total_revenue = sum(order.total for order in completed_orders)
            report += "3. ОБЩАЯ ВЫРУЧКА:\n"
            report += "-" * 40 + "\n"
            report += f"  Выполнено заказов: {len(completed_orders)}\n"
            report += f"  Выручка: {total_revenue:.2f} руб.\n\n"
            
            # Дополнительно: в доставке
            in_delivery_orders = [o for o in all_orders if o.status == OrderStatus.IN_DELIVERY.value]
            if in_delivery_orders:
                in_delivery_total = sum(o.total for o in in_delivery_orders)
                report += f"  В доставке: {len(in_delivery_orders)} заказов на {in_delivery_total:.2f} руб.\n\n"
            
            # Отменённые (информационно)
            cancelled_orders = [o for o in all_orders if o.status == OrderStatus.CANCELLED.value]
            if cancelled_orders:
                cancelled_total = sum(o.total for o in cancelled_orders)
                report += f"  Отменено: {len(cancelled_orders)} заказов на {cancelled_total:.2f} руб.\n"
                report += f"  (не учтено в выручке)\n"
        
        self.report_text.insert("1.0", report)
        self.report_text.configure(state=tk.DISABLED)


class MainApplication(tk.Tk):
    """Главное приложение"""
    
    def __init__(self):
        super().__init__()
        
        self.title("Быстрая доставка - Система учёта заказов")
        self.geometry("900x600")
        self.minsize(800, 500)
        
        # Настраиваем логгер
        setup_logger(log_file='logs/gui.log', level='INFO')
        
        # Подключаемся к БД
        self.db = self._create_database()
        
        # Создаём интерфейс
        self._create_menu()
        self._create_widgets()
        self._load_orders()
        
        logger.info("GUI приложение запущено")
        
        # Обработчик закрытия
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _create_database(self):
        """Создание подключения к БД"""
        try:
            # Проверяем какой тип БД использовать
            db_type = os.environ.get('DB_TYPE', 'sqlite')
            db_path = os.environ.get('DB_PATH', 'data/delivery.db' if db_type == 'sqlite' else 'data/tinydb.json')
            
            db = DatabaseFactory.create(db_type, db_path=db_path)
            db.connect()
            logger.info(f"Подключено к {db_type.upper()} базе данных")
            return db
        except Exception as e:
            logger.error(f"Ошибка подключения к БД: {e}")
            messagebox.showerror("Ошибка", f"Не удалось подключиться к базе данных:\n{e}")
            self.destroy()
            return None
    
    def _create_menu(self):
        """Создание меню"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # Меню Файл
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Экспорт в JSON", command=lambda: self._export_data('json'))
        file_menu.add_command(label="Экспорт в XML", command=lambda: self._export_data('xml'))
        file_menu.add_separator()
        file_menu.add_command(label="Импорт из JSON", command=lambda: self._import_data('json'))
        file_menu.add_command(label="Импорт из XML", command=lambda: self._import_data('xml'))
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self._on_closing)
        menubar.add_cascade(label="Файл", menu=file_menu)
        
        # Меню Справка
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="О программе", command=self._show_about)
        menubar.add_cascade(label="Справка", menu=help_menu)
    
    def _create_widgets(self):
        """Создание виджетов"""
        # Основной фрейм
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Фрейм для фильтров
        filter_frame = ttk.Frame(main_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(filter_frame, text="Фильтр по статусу:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.filter_var = tk.StringVar(value="Все")
        filter_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.filter_var,
            values=["Все"] + OrderStatus.choices(),
            state="readonly",
            width=20
        )
        filter_combo.pack(side=tk.LEFT, padx=(0, 10))
        filter_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_filter())
        
        ttk.Button(filter_frame, text="Применить", command=self._apply_filter).pack(side=tk.LEFT, padx=5)
        
        # Кнопка управления клиентами
        ttk.Button(filter_frame, text="Управление клиентами", command=self._manage_customers).pack(side=tk.RIGHT, padx=5)
        
        # Кнопка отчёта
        ttk.Button(filter_frame, text="Показать отчёт", command=self._show_report).pack(side=tk.RIGHT, padx=5)
        
        # TreeView для заказов
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("id", "customer", "date", "status", "total"),
            show="headings"
        )
        
        self.tree.heading("id", text="ID")
        self.tree.heading("customer", text="Клиент")
        self.tree.heading("date", text="Дата")
        self.tree.heading("status", text="Статус")
        self.tree.heading("total", text="Сумма")
        
        self.tree.column("id", width=50)
        self.tree.column("customer", width=200)
        self.tree.column("date", width=100)
        self.tree.column("status", width=120)
        self.tree.column("total", width=100)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Двойной клик для редактирования
        self.tree.bind("<Double-1>", lambda e: self._edit_order())
        
        # Кнопки управления
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(btn_frame, text="Добавить заказ", command=self._add_order).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Редактировать", command=self._edit_order).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Удалить", command=self._delete_order).pack(side=tk.LEFT, padx=5)
        
        # Статус бар
        self.status_var = tk.StringVar(value="Готово")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(10, 0))
    
    def _load_orders(self):
        """Загрузка заказов в TreeView"""
        # Очищаем TreeView
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Получаем заказы
        filter_status = self.filter_var.get()
        
        if filter_status == "Все":
            orders = self.db.get_all_orders()
        else:
            orders = self.db.get_orders_by_status(filter_status)
        
        # Получаем клиентов
        customers = {c.id: c for c in self.db.get_all_customers()}
        
        # Заполняем TreeView
        for order in orders:
            customer = customers.get(order.customer_id)
            customer_name = customer.name if customer else f"ID: {order.customer_id}"
            
            self.tree.insert("", "end", values=(
                order.id,
                customer_name,
                order.order_date,
                order.status,
                f"{order.total:.2f}"
            ))
        
        self.status_var.set(f"Загружено заказов: {len(orders)}")
    
    def _apply_filter(self):
        """Применение фильтра"""
        self._load_orders()
    
    def _add_order(self):
        """Добавление заказа"""
        # Проверяем есть ли клиенты
        customers = self.db.get_all_customers()
        if not customers:
            if messagebox.askyesno("Нет клиентов", "В базе нет клиентов. Добавить клиента?"):
                self._manage_customers()
            return
        
        dialog = OrderDialog(self, self.db)
        
        if dialog.result:
            try:
                self.db.create_order(dialog.result)
                self._load_orders()
                messagebox.showinfo("Успех", "Заказ успешно создан")
                logger.info(f"Создан заказ через GUI")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось создать заказ:\n{e}")
                logger.error(f"Ошибка создания заказа: {e}")
    
    def _edit_order(self):
        """Редактирование заказа"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите заказ для редактирования")
            return
        
        item = self.tree.item(selection[0])
        order_id = item["values"][0]
        
        order = self.db.get_order(order_id)
        if not order:
            messagebox.showerror("Ошибка", "Заказ не найден")
            return
        
        dialog = OrderDialog(self, self.db, order)
        
        if dialog.result:
            try:
                dialog.result.id = order_id
                self.db.update_order(dialog.result)
                self._load_orders()
                messagebox.showinfo("Успех", "Заказ успешно обновлён")
                logger.info(f"Обновлён заказ {order_id} через GUI")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось обновить заказ:\n{e}")
                logger.error(f"Ошибка обновления заказа {order_id}: {e}")
    
    def _delete_order(self):
        """Удаление заказа"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите заказ для удаления")
            return
        
        item = self.tree.item(selection[0])
        order_id = item["values"][0]
        
        if messagebox.askyesno("Подтверждение", f"Удалить заказ #{order_id}?"):
            try:
                self.db.delete_order(order_id)
                self._load_orders()
                messagebox.showinfo("Успех", "Заказ удалён")
                logger.info(f"Удалён заказ {order_id} через GUI")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить заказ:\n{e}")
                logger.error(f"Ошибка удаления заказа {order_id}: {e}")
    
    def _manage_customers(self):
        """Управление клиентами"""
        CustomerManagementDialog(self, self.db)
        self._load_orders()  # Обновить список (клиенты могут измениться)
    
    def _show_report(self):
        """Показать отчёт"""
        period = simpledialog.askstring(
            "Период отчёта",
            "Введите период (day/week/month):",
            initialvalue="month"
        )
        
        if period and period in ['day', 'week', 'month']:
            ReportDialog(self, self.db, period)
        elif period:
            messagebox.showerror("Ошибка", "Неверный период. Используйте: day, week, month")
    
    def _export_data(self, format_type: str):
        """Экспорт данных"""
        from tkinter import filedialog
        
        filepath = filedialog.asksaveasfilename(
            title="Экспорт данных",
            defaultextension=f".{format_type}",
            filetypes=[(f"{format_type.upper()} файлы", f"*.{format_type}")],
            initialfile=f"orders_export.{format_type}"
        )
        
        if filepath:
            try:
                exporter = DataExporter(self.db)
                if format_type == 'json':
                    success = exporter.export_to_json(filepath)
                else:
                    success = exporter.export_to_xml(filepath)
                
                if success:
                    messagebox.showinfo("Успех", f"Данные экспортированы в {filepath}")
                    logger.info(f"Экспорт в {format_type.upper()}: {filepath}")
                else:
                    messagebox.showerror("Ошибка", "Не удалось экспортировать данные")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка экспорта:\n{e}")
                logger.error(f"Ошибка экспорта: {e}")
    
    def _import_data(self, format_type: str):
        """Импорт данных"""
        from tkinter import filedialog
        
        filepath = filedialog.askopenfilename(
            title="Импорт данных",
            filetypes=[(f"{format_type.upper()} файлы", f"*.{format_type}")]
        )
        
        if filepath:
            try:
                importer = DataImporter(self.db)
                if format_type == 'json':
                    result = importer.import_from_json(filepath)
                else:
                    result = importer.import_from_xml(filepath)
                
                if result['success']:
                    self._load_orders()
                    messagebox.showinfo(
                        "Успех",
                        f"Импорт завершён:\n"
                        f"Клиентов: {result['customers_imported']}\n"
                        f"Заказов: {result['orders_imported']}"
                    )
                    logger.info(f"Импорт из {format_type.upper()}: {filepath}")
                else:
                    messagebox.showerror("Ошибка", f"Ошибка импорта:\n{result['errors']}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка импорта:\n{e}")
                logger.error(f"Ошибка импорта: {e}")
    
    def _show_about(self):
        """Показать информацию о программе"""
        messagebox.showinfo(
            "О программе",
            "Быстрая доставка\n"
            "Система учёта заказов\n\n"
            "Версия 1.0\n"
            "© 2025"
        )
    
    def _on_closing(self):
        """Обработчик закрытия приложения"""
        if messagebox.askokcancel("Выход", "Закрыть приложение?"):
            if self.db:
                self.db.disconnect()
            logger.info("GUI приложение закрыто")
            self.destroy()


def main():
    """Точка входа в GUI приложение"""
    app = MainApplication()
    app.mainloop()


if __name__ == '__main__':
    main()