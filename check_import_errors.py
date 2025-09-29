import time
import subprocess

print("Ожидание запуска Airflow...")
time.sleep(30)

print("Проверка ошибок импорта...")
try:
    result = subprocess.run(['docker', 'exec', 'aie_airflow', 'airflow', 'dags', 'list-import-errors'], 
                          capture_output=True, text=True, timeout=30)
    
    if "dag_generator.py" in result.stdout:
        print("❌ Ошибка импорта dag_generator.py все еще есть")
        print(result.stdout)
    else:
        print("✅ Ошибки импорта dag_generator.py исправлены")
        
    # Проверяем список DAG'ов
    result2 = subprocess.run(['docker', 'exec', 'aie_airflow', 'airflow', 'dags', 'list'], 
                           capture_output=True, text=True, timeout=30)
    
    if "test_module" in result2.stdout:
        lines = [line for line in result2.stdout.split('\n') if 'test_module' in line]
        print(f"\n✅ Найдено {len(lines)} тестовых DAG'ов:")
        for line in lines:
            print(f"  {line.split()[0]}")
    else:
        print("\n❌ Тестовые DAG'и не найдены")
        
except Exception as e:
    print(f"Ошибка: {e}")
