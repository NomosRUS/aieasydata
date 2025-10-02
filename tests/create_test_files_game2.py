"""
Создание тестовых файлов для второго игрового теста модуля 2.
Создает файлы с 100+ строками в папках syn_csv, syn_json, syn_xml.
"""

import json
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timedelta
import random

def create_csv_file():
    """Создает CSV файл с данными о транзакциях."""
    
    csv_dir = Path("data_landing_zone/syn_csv")
    csv_dir.mkdir(parents=True, exist_ok=True)
    
    csv_file = csv_dir / "transactions.csv"
    
    # Генерируем 120 строк данных
    data = []
    base_date = datetime(2023, 1, 1)
    
    for i in range(120):
        transaction = {
            'transaction_id': f'TXN_{i+1:04d}',
            'user_id': f'USER_{random.randint(1, 50):03d}',
            'amount': round(random.uniform(10.0, 1000.0), 2),
            'currency': random.choice(['USD', 'EUR', 'GBP', 'RUB']),
            'transaction_date': (base_date + timedelta(days=i)).strftime('%Y-%m-%d'),
            'transaction_time': f'{random.randint(0, 23):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}',
            'merchant': random.choice(['Amazon', 'eBay', 'PayPal', 'Stripe', 'Square']),
            'category': random.choice(['Shopping', 'Food', 'Transport', 'Entertainment', 'Bills']),
            'status': random.choice(['completed', 'pending', 'failed']),
            'payment_method': random.choice(['credit_card', 'debit_card', 'paypal', 'bank_transfer'])
        }
        data.append(transaction)
    
    # Записываем в CSV
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    
    print(f"CSV файл создан: {csv_file}")
    print(f"Строк данных: {len(data)}")
    print(f"Колонки: {list(data[0].keys())}")
    
    return str(csv_file)

def create_json_file():
    """Создает JSON файл с данными о пользователях."""
    
    json_dir = Path("data_landing_zone/syn_json")
    json_dir.mkdir(parents=True, exist_ok=True)
    
    json_file = json_dir / "users.json"
    
    # Генерируем 110 записей пользователей
    users = []
    
    for i in range(110):
        user = {
            'user_id': f'USER_{i+1:03d}',
            'username': f'user_{i+1}',
            'email': f'user{i+1}@example.com',
            'first_name': random.choice(['John', 'Jane', 'Mike', 'Sarah', 'David', 'Lisa', 'Tom', 'Anna']),
            'last_name': random.choice(['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis']),
            'age': random.randint(18, 65),
            'country': random.choice(['USA', 'UK', 'Germany', 'France', 'Canada', 'Australia', 'Russia', 'Japan']),
            'city': random.choice(['New York', 'London', 'Berlin', 'Paris', 'Toronto', 'Sydney', 'Moscow', 'Tokyo']),
            'registration_date': (datetime(2022, 1, 1) + timedelta(days=random.randint(0, 365))).strftime('%Y-%m-%d'),
            'is_active': random.choice([True, False]),
            'subscription_type': random.choice(['free', 'premium', 'enterprise']),
            'last_login': (datetime.now() - timedelta(days=random.randint(0, 30))).strftime('%Y-%m-%d %H:%M:%S')
        }
        users.append(user)
    
    # Записываем в JSON
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)
    
    print(f"JSON файл создан: {json_file}")
    print(f"Записей: {len(users)}")
    print(f"Поля: {list(users[0].keys())}")
    
    return str(json_file)

def create_xml_file():
    """Создает XML файл с данными о заказах."""
    
    xml_dir = Path("data_landing_zone/syn_xml")
    xml_dir.mkdir(parents=True, exist_ok=True)
    
    xml_file = xml_dir / "orders.xml"
    
    # Создаем корневой элемент
    root = ET.Element("orders")
    
    # Генерируем 105 заказов
    for i in range(105):
        order = ET.SubElement(root, "order")
        
        # Добавляем поля заказа
        ET.SubElement(order, "order_id").text = f"ORD_{i+1:04d}"
        ET.SubElement(order, "customer_id").text = f"CUST_{random.randint(1, 100):03d}"
        ET.SubElement(order, "product_name").text = random.choice([
            'Laptop Pro', 'Smartphone X', 'Tablet Air', 'Headphones Max', 
            'Camera Digital', 'Watch Smart', 'Speaker Bluetooth', 'Monitor 4K'
        ])
        ET.SubElement(order, "quantity").text = str(random.randint(1, 5))
        ET.SubElement(order, "unit_price").text = str(round(random.uniform(50.0, 2000.0), 2))
        ET.SubElement(order, "total_amount").text = str(round(random.uniform(100.0, 5000.0), 2))
        ET.SubElement(order, "order_date").text = (datetime(2023, 1, 1) + timedelta(days=random.randint(0, 300))).strftime('%Y-%m-%d')
        ET.SubElement(order, "shipping_address").text = f"{random.randint(1, 999)} Main St, City {random.randint(1, 50)}"
        ET.SubElement(order, "order_status").text = random.choice(['pending', 'processing', 'shipped', 'delivered', 'cancelled'])
        ET.SubElement(order, "payment_status").text = random.choice(['paid', 'pending', 'failed'])
        ET.SubElement(order, "shipping_method").text = random.choice(['standard', 'express', 'overnight'])
        ET.SubElement(order, "discount_applied").text = str(round(random.uniform(0.0, 50.0), 2))
    
    # Записываем в XML файл
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ", level=0)
    tree.write(xml_file, encoding='utf-8', xml_declaration=True)
    
    print(f"XML файл создан: {xml_file}")
    print(f"Заказов: {len(root)}")
    
    # Показываем поля первого заказа
    first_order = root[0]
    fields = [child.tag for child in first_order]
    print(f"Поля: {fields}")
    
    return str(xml_file)

def main():
    """Создает все тестовые файлы."""
    
    print("СОЗДАНИЕ ТЕСТОВЫХ ФАЙЛОВ ДЛЯ ИГРОВОГО ТЕСТА 2")
    print("=" * 60)
    
    # Создаем файлы
    csv_path = create_csv_file()
    print()
    json_path = create_json_file()
    print()
    xml_path = create_xml_file()
    
    print("\n" + "=" * 60)
    print("ВСЕ ТЕСТОВЫЕ ФАЙЛЫ СОЗДАНЫ УСПЕШНО!")
    print("=" * 60)
    print(f"CSV:  {csv_path}")
    print(f"JSON: {json_path}")
    print(f"XML:  {xml_path}")
    
    return {
        'csv': csv_path,
        'json': json_path,
        'xml': xml_path
    }

if __name__ == "__main__":
    main()
