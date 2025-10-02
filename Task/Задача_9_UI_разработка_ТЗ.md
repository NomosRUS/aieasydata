# ЗАДАЧА 9: Разработка UI для управления данными и взаимодействия с ИИ-агентом

**Исполнитель**: Команда разработчиков  
**Ветка Git**: `feature/ui-development`  
**Расположение модуля**: `ui/src/`

## **1. Цель и концепция**

Разработать пользовательский интерфейс `data_management_ui`, который обеспечивает полное управление данными и взаимодействие с ИИ-агентом. UI будет выполнять четыре ключевые функции:

1. **Управление данными**: Загрузка, выгрузка и удаление данных через интуитивный интерфейс
2. **Управление пайплайнами**: Просмотр, создание и удаление ETL пайплайнов и DAG'ов
3. **ИИ-чат интерфейс**: Взаимодействие с агентом для создания новых пайплайнов
4. **Мониторинг и визуализация**: Отображение статуса выполнения и метрик системы

**Уровень реализации**: **Базовый**. Основной фокус — на создании функционального UI с базовыми возможностями управления.

## **2. Архитектурное место в системе**

- Все новые файлы для этого модуля будут размещаться в директории: `ui/src/`
- UI взаимодействует с backend через REST API
- Использует React + Vite для быстрой разработки
- Интегрируется с ИИ-агентом через WebSocket для real-time чата

## **3. Основные экраны и компоненты**

### **3.1. Главная панель (Dashboard)**
- **Функция**: Обзор системы и быстрый доступ к основным функциям
- **Компоненты**: Статистика данных, активные пайплайны, последние действия
- **Виджеты**: Графики загрузки, статус модулей, уведомления

### **3.2. Управление данными (Data Management)**
- **Загрузка файлов**: Drag & drop интерфейс для CSV, JSON, XML
- **Просмотр данных**: Таблицы с пагинацией и фильтрацией
- **Удаление данных**: Безопасное удаление с подтверждением

### **3.3. Пайплайны (Pipelines)**
- **Список пайплайнов**: Все созданные ETL процессы и DAG'и
- **Статус выполнения**: Real-time мониторинг прогресса
- **Управление**: Запуск, остановка, удаление пайплайнов

### **3.4. ИИ-ассистент (AI Chat)**
- **Чат интерфейс**: Диалог с агентом в стиле ChatGPT
- **Создание пайплайнов**: Генерация через естественный язык
- **Визуализация планов**: Схематичное отображение предлагаемых решений

## **4. Архитектура UI**

```
ui/src/
├── components/                    # Переиспользуемые компоненты
│   ├── common/                    # Общие компоненты
│   │   ├── Header.jsx
│   │   ├── Sidebar.jsx
│   │   ├── LoadingSpinner.jsx
│   │   └── ErrorBoundary.jsx
│   ├── data/                      # Компоненты для данных
│   │   ├── FileUpload.jsx
│   │   ├── DataTable.jsx
│   │   ├── DataPreview.jsx
│   │   └── DeleteConfirmation.jsx
│   ├── pipelines/                 # Компоненты пайплайнов
│   │   ├── PipelineList.jsx
│   │   ├── PipelineCard.jsx
│   │   ├── StatusBadge.jsx
│   │   └── ExecutionProgress.jsx
│   └── ai/                        # ИИ компоненты
│       ├── ChatInterface.jsx
│       ├── MessageBubble.jsx
│       ├── PlanVisualization.jsx
│       └── SuggestionCard.jsx
├── pages/                         # Основные страницы
│   ├── Dashboard.jsx
│   ├── DataManagement.jsx
│   ├── Pipelines.jsx
│   ├── AIAssistant.jsx
│   └── Settings.jsx
├── services/                      # API клиенты
│   ├── api.js                     # Основной API клиент
│   ├── dataService.js             # Управление данными
│   ├── pipelineService.js         # Управление пайплайнами
│   └── aiService.js               # ИИ-агент API
├── hooks/                         # React hooks
│   ├── useApi.js
│   ├── useWebSocket.js
│   └── useLocalStorage.js
├── utils/                         # Утилиты
│   ├── formatters.js
│   ├── validators.js
│   └── constants.js
├── styles/                        # Стили
│   ├── globals.css
│   └── components.css
├── App.jsx                        # Главный компонент
└── main.jsx                       # Точка входа
```

## **5. Основные компоненты**

### **5.1. FileUpload (components/data/FileUpload.jsx)**
**Назначение:** Drag & drop загрузка файлов

```jsx
const FileUpload = ({ onUpload, acceptedTypes = ['.csv', '.json', '.xml'] }) => {
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  
  const handleDrop = async (files) => {
    setUploading(true);
    try {
      const results = await Promise.all(
        files.map(file => dataService.uploadFile(file))
      );
      onUpload(results);
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className={`upload-zone ${dragActive ? 'active' : ''}`}>
      {uploading ? (
        <LoadingSpinner message="Загрузка файлов..." />
      ) : (
        <div className="upload-content">
          <h3>Перетащите файлы сюда или нажмите для выбора</h3>
          <p>Поддерживаемые форматы: {acceptedTypes.join(', ')}</p>
        </div>
      )}
    </div>
  );
};
```

### **5.2. ChatInterface (components/ai/ChatInterface.jsx)**
**Назначение:** Интерфейс чата с ИИ-агентом

```jsx
const ChatInterface = () => {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const { sendMessage, isConnected } = useWebSocket('/api/v1/agent/chat');

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;
    
    const userMessage = { type: 'user', content: inputValue, timestamp: new Date() };
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsTyping(true);

    try {
      const response = await aiService.sendMessage(inputValue);
      const agentMessage = { 
        type: 'agent', 
        content: response.response, 
        plan: response.execution_plan,
        timestamp: new Date() 
      };
      setMessages(prev => [...prev, agentMessage]);
    } catch (error) {
      console.error('Failed to send message:', error);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="chat-interface">
      <div className="messages-container">
        {messages.map((message, index) => (
          <MessageBubble key={index} message={message} />
        ))}
        {isTyping && <TypingIndicator />}
      </div>
      <div className="input-container">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
          placeholder="Опишите что вы хотите сделать с данными..."
        />
        <button onClick={handleSendMessage} disabled={!inputValue.trim()}>
          Отправить
        </button>
      </div>
    </div>
  );
};
```

### **5.3. PipelineList (components/pipelines/PipelineList.jsx)**
**Назначение:** Список всех пайплайнов с управлением

```jsx
const PipelineList = () => {
  const [pipelines, setPipelines] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPipelines();
  }, []);

  const loadPipelines = async () => {
    try {
      const data = await pipelineService.getAllPipelines();
      setPipelines(data);
    } catch (error) {
      console.error('Failed to load pipelines:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDeletePipeline = async (pipelineId) => {
    if (window.confirm('Вы уверены, что хотите удалить этот пайплайн?')) {
      try {
        await pipelineService.deletePipeline(pipelineId);
        setPipelines(prev => prev.filter(p => p.id !== pipelineId));
      } catch (error) {
        console.error('Failed to delete pipeline:', error);
      }
    }
  };

  return (
    <div className="pipeline-list">
      <div className="list-header">
        <h2>Пайплайны обработки данных</h2>
        <button className="create-btn">Создать новый</button>
      </div>
      
      {loading ? (
        <LoadingSpinner />
      ) : (
        <div className="pipelines-grid">
          {pipelines.map(pipeline => (
            <PipelineCard
              key={pipeline.id}
              pipeline={pipeline}
              onDelete={handleDeletePipeline}
            />
          ))}
        </div>
      )}
    </div>
  );
};
```

## **6. API интеграция**

### **6.1. Основной API клиент (services/api.js)**
```javascript
class ApiClient {
  constructor(baseURL = 'http://localhost:8000') {
    this.baseURL = baseURL;
    this.token = localStorage.getItem('auth_token');
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...(this.token && { 'Authorization': `Bearer ${this.token}` }),
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Методы для разных типов запросов
  get(endpoint) { return this.request(endpoint); }
  post(endpoint, data) { 
    return this.request(endpoint, { 
      method: 'POST', 
      body: JSON.stringify(data) 
    }); 
  }
  delete(endpoint) { return this.request(endpoint, { method: 'DELETE' }); }
}

export const api = new ApiClient();
```

### **6.2. Сервис управления данными (services/dataService.js)**
```javascript
export const dataService = {
  async uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('/api/v1/data/upload', {
      method: 'POST',
      body: formData,
    });
    
    return response.json();
  },

  async getDataSources() {
    return api.get('/api/v1/data/sources');
  },

  async deleteDataSource(sourceId) {
    return api.delete(`/api/v1/data/sources/${sourceId}`);
  },

  async previewData(sourceId, limit = 100) {
    return api.get(`/api/v1/data/preview/${sourceId}?limit=${limit}`);
  }
};
```

### **6.3. Сервис ИИ-агента (services/aiService.js)**
```javascript
export const aiService = {
  async sendMessage(message, sessionId = null) {
    return api.post('/api/v1/agent/chat', {
      message,
      session_id: sessionId,
      context: {
        timestamp: new Date().toISOString()
      }
    });
  },

  async executeAgentPlan(planId) {
    return api.post('/api/v1/agent/execute', {
      plan_id: planId,
      confirm_execution: true
    });
  },

  async getExecutionStatus(executionId) {
    return api.get(`/api/v1/agent/status/${executionId}`);
  },

  async generateDAG(planId, schedule, name) {
    return api.post('/api/v1/agent/generate-dag', {
      plan_id: planId,
      schedule,
      dag_name: name
    });
  }
};
```

## **7. Основные страницы**

### **7.1. Dashboard (pages/Dashboard.jsx)**
```jsx
const Dashboard = () => {
  const [stats, setStats] = useState({});
  const [recentActivity, setRecentActivity] = useState([]);

  return (
    <div className="dashboard">
      <div className="stats-grid">
        <StatCard title="Источники данных" value={stats.dataSources} />
        <StatCard title="Активные пайплайны" value={stats.activePipelines} />
        <StatCard title="Обработано данных" value={stats.processedData} />
        <StatCard title="Успешных выполнений" value={stats.successRate} />
      </div>
      
      <div className="dashboard-content">
        <div className="recent-activity">
          <h3>Последняя активность</h3>
          <ActivityList activities={recentActivity} />
        </div>
        
        <div className="quick-actions">
          <h3>Быстрые действия</h3>
          <button onClick={() => navigate('/data')}>Загрузить данные</button>
          <button onClick={() => navigate('/ai')}>Создать пайплайн</button>
        </div>
      </div>
    </div>
  );
};
```

### **7.2. DataManagement (pages/DataManagement.jsx)**
```jsx
const DataManagement = () => {
  const [dataSources, setDataSources] = useState([]);
  const [selectedSource, setSelectedSource] = useState(null);

  return (
    <div className="data-management">
      <div className="data-sidebar">
        <FileUpload onUpload={handleFileUpload} />
        <DataSourceList 
          sources={dataSources}
          onSelect={setSelectedSource}
          onDelete={handleDeleteSource}
        />
      </div>
      
      <div className="data-content">
        {selectedSource ? (
          <DataPreview source={selectedSource} />
        ) : (
          <div className="empty-state">
            <h3>Выберите источник данных для просмотра</h3>
          </div>
        )}
      </div>
    </div>
  );
};
```

## **8. Стилизация и UX**

### **8.1. Основные стили (styles/globals.css)**
```css
:root {
  --primary-color: #2563eb;
  --secondary-color: #64748b;
  --success-color: #10b981;
  --warning-color: #f59e0b;
  --error-color: #ef4444;
  --background-color: #f8fafc;
  --card-background: #ffffff;
  --border-color: #e2e8f0;
  --text-primary: #1e293b;
  --text-secondary: #64748b;
}

.upload-zone {
  border: 2px dashed var(--border-color);
  border-radius: 8px;
  padding: 2rem;
  text-align: center;
  transition: all 0.3s ease;
  cursor: pointer;
}

.upload-zone.active {
  border-color: var(--primary-color);
  background-color: rgba(37, 99, 235, 0.05);
}

.chat-interface {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--card-background);
  border-radius: 8px;
  overflow: hidden;
}

.messages-container {
  flex: 1;
  padding: 1rem;
  overflow-y: auto;
}

.pipeline-card {
  background: var(--card-background);
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s ease;
}

.pipeline-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
```

## **9. Тестирование**

**Интеграционный тест:** `test_ui_integration.js`

**Проверяемые сценарии:**
1. ✅ Загрузка и отображение файлов
2. ✅ Взаимодействие с ИИ-агентом через чат
3. ✅ Создание и управление пайплайнами
4. ✅ Мониторинг выполнения задач
5. ✅ Удаление данных и пайплайнов
6. ✅ Responsive дизайн на разных устройствах
7. ✅ Обработка ошибок и edge cases

## **10. План работ**

### **Этап 1: Базовая структура и компоненты (2 часа)**
1. Настроить React + Vite проект
2. Создать основные компоненты и страницы
3. Реализовать навигацию и роутинг
4. Добавить базовые стили и layout

### **Этап 2: Управление данными (2 часа)**
1. Реализовать FileUpload с drag & drop
2. Создать DataTable для просмотра данных
3. Добавить функции удаления с подтверждением
4. Интегрировать с backend API

### **Этап 3: ИИ-чат и пайплайны (1 час)**
1. Создать ChatInterface для общения с агентом
2. Реализовать PipelineList с управлением
3. Добавить мониторинг статуса выполнения
4. Настроить WebSocket для real-time обновлений

### **Этап 4: Полировка и тестирование (1 час)**
1. Добавить обработку ошибок и loading состояния
2. Оптимизировать производительность
3. Провести тестирование на разных браузерах
4. Добавить документацию по использованию

**Общее время разработки:** 6 часов (базовый уровень сложности)

---

**СТАТУС ТЗ:** 📋 ГОТОВО К РЕАЛИЗАЦИИ

**UI спроектирован для обеспечения интуитивного управления всеми аспектами системы AiEasyData с особым акцентом на взаимодействие с ИИ-агентом и простоту использования.**
