#!/usr/bin/env python3
"""
CLI интерфейс для системы учёта заказов «Быстрая доставка»

Примеры использования:
    python main_cli.py report --period month
    python main_cli.py export --file orders_backup.xml
    python main_cli.py import --file orders_new.json
"""

import argparse
import sys
from datetime import datetime, timedelta
from typing import Dict, Any

from database import DatabaseFactory, SQLiteDatabase, TinyDBDatabase
from models import OrderStatus
from logger_config import logger, setup_logger
from data_export import export_data, import_data


def get_db_instance(db_type: str, db_path: str):
    """
    Создание экземпляра базы данных
    
    Args:
        db_type: Тип БД ('sqlite' или 'tinydb')
        db_path: Путь к файлу БД
    
    Returns:
        Экземпляр базы данных
    """
    try:
        db = DatabaseFactory.create(db_type, db_path=db_path)
        db.connect()
        logger.info(f"Подключено к {db_type.upper()} базе данных: {db_path}")
        return db
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        print(f"Ошибка подключения к базе данных: {e}")
        sys.exit(1)


def cmd_report(args, db):
    """
    Обработчик команды report - генерация отчётов
    
    Args:
        args: Аргументы командной строки
        db: Экземпляр базы данных
    """
    period = args.period
    
    # Определяем диапазон дат
    today = datetime.now().date()
    
    if period == 'day':
        start_date = today
        end_date = today
        period_name = "сегодня"
    elif period == 'week':
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
        period_name = "эту неделю"
    elif period == 'month':
        start_date = today.replace(day=1)
        if today.month == 12:
            end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end_date = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        period_name = "этот месяц"
    else:
        logger.error(f"Неверный период: {period}")
        print(f"Ошибка: неверный период '{period}'. Используйте: day, week, month")
        return False
    
    start_date_str = start_date.isoformat()
    end_date_str = end_date.isoformat()
    
    print(f"\n{'='*60}")
    print(f"ОТЧЁТ ЗА {period_name.upper()}")
    print(f"Период: {start_date} - {end_date}")
    print(f"{'='*60}\n")
    
    # Получаем ВСЕ заказы за период
    all_orders = db.get_orders_by_date_range(start_date_str, end_date_str)
    
    if not all_orders:
        print("Заказов за указанный период не найдено.")
        return True
    
    # 1. Количество заказов по статусам (показываем ВСЕ)
    print("1. КОЛИЧЕСТВО ЗАКАЗОВ ПО СТАТУСАМ:")
    print("-" * 40)
    
    status_counts = {}
    for order in all_orders:
        status_counts[order.status] = status_counts.get(order.status, 0) + 1
    
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")
    print(f"  Итого: {len(all_orders)}")
    
    # Фильтруем заказы для финансовых расчётов
    # Исключаем отменённые заказы из выручки и статистики клиентов
    active_orders = [o for o in all_orders if o.status != OrderStatus.CANCELLED.value]
    completed_orders = [o for o in all_orders if o.status == OrderStatus.COMPLETED.value]
    
    # 2. Топ-3 клиента по сумме заказов (только активные: выполненные + в доставке)
    print(f"\n2. ТОП-3 КЛИЕНТА ПО СУММЕ ЗАКАЗОВ:")
    print(f"   (учитываются только выполненные и в доставке)")
    print("-" * 40)
    
    customers = {c.id: c for c in db.get_all_customers()}
    customer_totals = {}
    
    for order in active_orders:
        if order.customer_id not in customer_totals:
            customer_totals[order.customer_id] = 0
        customer_totals[order.customer_id] += order.total
    
    # Сортируем по сумме и берём топ-3
    sorted_customers = sorted(customer_totals.items(), key=lambda x: x[1], reverse=True)[:3]
    
    if sorted_customers:
        for i, (customer_id, total) in enumerate(sorted_customers, 1):
            customer = customers.get(customer_id)
            if customer:
                print(f"  {i}. {customer.name} - {total:.2f} руб.")
    else:
        print("  Нет активных заказов")
    
    # 3. Общая выручка (только выполненные заказы)
    print(f"\n3. ОБЩАЯ ВЫРУЧКА:")
    print("-" * 40)
    
    total_revenue = sum(order.total for order in completed_orders)
    print(f"  Выполнено заказов: {len(completed_orders)}")
    print(f"  Выручка: {total_revenue:.2f} руб.")
    
    # Дополнительно: выручка в доставке
    in_delivery_orders = [o for o in all_orders if o.status == OrderStatus.IN_DELIVERY.value]
    if in_delivery_orders:
        in_delivery_total = sum(o.total for o in in_delivery_orders)
        print(f"\n  В доставке: {len(in_delivery_orders)} заказов на {in_delivery_total:.2f} руб.")
    
    # Отменённые заказы (информационно)
    cancelled_orders = [o for o in all_orders if o.status == OrderStatus.CANCELLED.value]
    if cancelled_orders:
        cancelled_total = sum(o.total for o in cancelled_orders)
        print(f"\n  Отменено: {len(cancelled_orders)} заказов на {cancelled_total:.2f} руб.")
        print(f"  (не учтено в выручке)")
    
    # 4. Детализация по дням (только активные заказы)
    print(f"\n4. ДЕТАЛИЗАЦИЯ ПО ДНЯМ (активные заказы):")
    print("-" * 40)
    
    daily_totals = {}
    daily_counts = {}
    for order in active_orders:
        date = order.order_date
        daily_totals[date] = daily_totals.get(date, 0) + order.total
        daily_counts[date] = daily_counts.get(date, 0) + 1
    
    if daily_totals:
        for date in sorted(daily_totals.keys()):
            count = daily_counts[date]
            total = daily_totals[date]
            print(f"  {date}: {count} заказов, {total:.2f} руб.")
    else:
        print("  Нет активных заказов")
    
    print(f"\n{'='*60}\n")
    
    logger.info(
        f"Отчёт за {period_name} сформирован: "
        f"всего {len(all_orders)} заказов, "
        f"выручка {total_revenue:.2f} руб. (выполнено {len(completed_orders)})"
    )
    return True


def cmd_export(args, db):
    """
    Обработчик команды export - экспорт данных
    
    Args:
        args: Аргументы командной строки
        db: Экземпляр базы данных
    """
    filepath = args.file
    
    # Определяем формат по расширению файла
    if filepath.lower().endswith('.json'):
        format_type = 'json'
    elif filepath.lower().endswith('.xml'):
        format_type = 'xml'
    else:
        # Если расширение не указано, используем JSON
        format_type = 'json'
        if not filepath.lower().endswith(('.json', '.xml')):
            filepath += '.json'
    
    print(f"\nЭкспорт данных в файл: {filepath}")
    print(f"Формат: {format_type.upper()}")
    
    success = export_data(db, filepath, format_type)
    
    if success:
        print("✓ Экспорт успешно завершён!")
        logger.info(f"Экспорт в {format_type.upper()} выполнен: {filepath}")
        return True
    else:
        print("✗ Ошибка при экспорте данных")
        logger.error(f"Экспорт в {format_type.upper()} не удался: {filepath}")
        return False


def cmd_import(args, db):
    """
    Обработчик команды import - импорт данных
    
    Args:
        args: Аргументы командной строки
        db: Экземпляр базы данных
    """
    filepath = args.file
    skip_existing = not args.overwrite
    
    # Определяем формат по расширению файла
    if filepath.lower().endswith('.json'):
        format_type = 'json'
    elif filepath.lower().endswith('.xml'):
        format_type = 'xml'
    else:
        print(f"Ошибка: неверный формат файла. Используйте .json или .xml")
        return False
    
    print(f"\nИмпорт данных из файла: {filepath}")
    print(f"Формат: {format_type.upper()}")
    if skip_existing:
        print("Режим: пропуск существующих заказов")
    else:
        print("Режим: перезапись существующих заказов")
    
    result = import_data(db, filepath, format_type, skip_existing=skip_existing)
    
    if result['success']:
        print("\n✓ Импорт успешно завершён!")
        print(f"  Импортировано клиентов: {result['customers_imported']}")
        print(f"  Импортировано заказов: {result['orders_imported']}")
        if result['orders_skipped'] > 0:
            print(f"  Пропущено заказов: {result['orders_skipped']}")
        
        if result['errors']:
            print(f"\n  Предупреждений: {len(result['errors'])}")
            for error in result['errors'][:5]:  # Показываем первые 5 ошибок
                print(f"    - {error}")
            if len(result['errors']) > 5:
                print(f"    ... и ещё {len(result['errors']) - 5}")
        
        logger.info(
            f"Импорт из {format_type.upper()} завершён: "
            f"{result['customers_imported']} клиентов, "
            f"{result['orders_imported']} заказов"
        )
        return True
    else:
        print("\n✗ Ошибка при импорте данных:")
        for error in result['errors']:
            print(f"  - {error}")
        logger.error(f"Импорт из {format_type.upper()} не удался: {result['errors']}")
        return False


def create_parser():
    """
    Создание парсера аргументов командной строки
    
    Returns:
        ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog='delivery_system',
        description='Система учёта заказов «Быстрая доставка»',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Примеры использования:
  %(prog)s report --period month
  %(prog)s export --file orders_backup.xml
  %(prog)s import --file orders_new.json --overwrite
        '''
    )
    
    # Общий аргумент для выбора типа БД
    parser.add_argument(
        '--db',
        choices=['sqlite', 'tinydb'],
        default='sqlite',
        help='Тип базы данных (по умолчанию: sqlite)'
    )
    
    parser.add_argument(
        '--db-path',
        default=None,
        help='Путь к файлу базы данных'
    )
    
    # Подкоманды
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
    
    # Команда report
    report_parser = subparsers.add_parser(
        'report',
        help='Сформировать отчёт',
        description='Генерация отчёта по заказам за указанный период'
    )
    report_parser.add_argument(
        '--period',
        choices=['day', 'week', 'month'],
        required=True,
        help='Период отчёта: day (сегодня), week (эта неделя), month (этот месяц)'
    )
    
    # Команда export
    export_parser = subparsers.add_parser(
        'export',
        help='Экспорт данных',
        description='Экспорт всех заказов в XML или JSON формат'
    )
    export_parser.add_argument(
        '--file', '-f',
        required=True,
        help='Путь к файлу для экспорта (расширение .xml или .json)'
    )
    
    # Команда import
    import_parser = subparsers.add_parser(
        'import',
        help='Импорт данных',
        description='Импорт заказов из XML или JSON файла'
    )
    import_parser.add_argument(
        '--file', '-f',
        required=True,
        help='Путь к файлу для импорта (.xml или .json)'
    )
    import_parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Перезаписать существующие заказы (по умолчанию: пропускать)'
    )
    
    return parser


def main():
    """Точка входа в CLI приложение"""
    parser = create_parser()
    args = parser.parse_args()
    
    # Если команда не указана, показываем справку
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    # Настраиваем логгер
    setup_logger(log_file='logs/cli.log', level='INFO')
    
    # Определяем путь к БД
    if args.db_path is None:
        if args.db == 'sqlite':
            db_path = 'data/delivery.db'
        else:
            db_path = 'data/tinydb.json'
    else:
        db_path = args.db_path
    
    # Подключаемся к БД
    db = get_db_instance(args.db, db_path)
    
    try:
        # Выполняем команду
        if args.command == 'report':
            success = cmd_report(args, db)
        elif args.command == 'export':
            success = cmd_export(args, db)
        elif args.command == 'import':
            success = cmd_import(args, db)
        else:
            print(f"Неизвестная команда: {args.command}")
            success = False
        
        # Выход с соответствующим кодом
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
        logger.warning("Выполнение прервано пользователем")
        sys.exit(130)
    except Exception as e:
        print(f"\nНеожиданная ошибка: {e}")
        logger.exception(f"Неожиданная ошибка: {e}")
        sys.exit(1)
    finally:
        # Отключаемся от БД
        try:
            db.disconnect()
        except:
            pass


if __name__ == '__main__':
    main()