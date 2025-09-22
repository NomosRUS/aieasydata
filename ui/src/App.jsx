import React, { useState, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';

const API_BASE_URL = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

const DataSourceCard = ({ source, onAnalyze }) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleAnalyzeClick = async () => {
    setIsLoading(true);
    await onAnalyze(source.id);
    setIsLoading(false);
  };

  return (
    <div style={styles.card}>
      <h3 style={styles.cardTitle}>{source.source_path.split('/').pop()}</h3>
      <div style={styles.cardBody}>
        <p><strong>ID:</strong> {source.id}</p>
        <p><strong>Путь:</strong> {source.source_path}</p>
        <p><strong>Тип:</strong> {source.kind || 'N/A'}</p>
        <p><strong>Всего строк:</strong> {source.total_row_count?.toLocaleString() || 'N/A'}</p>
        <p><strong>Кол-во файлов:</strong> {source.file_count || 'N/A'}</p>
        <p><strong>Создано:</strong> {new Date(source.created_at).toLocaleString('ru-RU')}</p>
        <p><strong>Обновлено:</strong> {new Date(source.updated_at).toLocaleString('ru-RU')}</p>

        {source.error && <p style={{color: 'red', whiteSpace: 'pre-wrap'}}><strong>Ошибка профилирования:</strong> {source.error}</p>}

        {source.llm_summary && (
          <div style={styles.summarySection}>
            <h4>Анализ LLM:</h4>
            <ReactMarkdown>{source.llm_summary}</ReactMarkdown>
          </div>
        )}

      </div>
      <div style={styles.cardFooter}>
        <button onClick={handleAnalyzeClick} disabled={isLoading} style={styles.button}>
          {isLoading ? 'Анализ...' : (source.llm_summary ? 'Переанализировать' : 'Анализировать')}
        </button>
      </div>
    </div>
  );
};

const App = () => {
  const [dataSources, setDataSources] = useState([]);
  const [error, setError] = useState('');
  const [isDagRunning, setIsDagRunning] = useState(false);

  const fetchDataInventory = async () => {
    try {
      setError('');
      const response = await axios.get(`${API_BASE_URL}/api/data-inventory`);
      setDataSources(response.data.data || []);
    } catch (err) {
      setError('Не удалось загрузить каталог данных. Убедитесь, что API доступен.');
      console.error(err);
    }
  };

  const handleTriggerDag = async () => {
    setIsDagRunning(true);
    setError('');
    try {
      await axios.post(`${API_BASE_URL}/api/trigger-dag/data_profiling_pipeline`);
      // Give it a moment before refetching
      setTimeout(() => {
        fetchDataInventory();
      }, 3000); // 3 seconds delay
    } catch (err) {
      setError('Не удалось запустить DAG. Проверьте консоль и логи API.');
      console.error('Ошибка при запуске DAG:', err);
    } finally {
      // Keep the button disabled for a few seconds to prevent spamming
      setTimeout(() => setIsDagRunning(false), 5000);
    }
  };

  useEffect(() => {
    fetchDataInventory();
  }, []);

  const handleAnalyze = async (sourceId) => {
    try {
      setError('');
      // Используем новый, правильный эндпоинт
      const response = await axios.post(`${API_BASE_URL}/api/analyze-profile/${sourceId}`);
      setDataSources(prevSources => 
        prevSources.map(source => 
          source.id === sourceId ? response.data : source
        )
      );
    } catch (err) {
      setError('Ошибка при анализе источника данных. Проверьте консоль браузера и логи API.');
      console.error('Ошибка в handleAnalyze:', err);
    }
  };

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1>Каталог Данных</h1>
        <p>Обнаруженные источники данных в Data Landing Zone</p>
        <button onClick={handleTriggerDag} disabled={isDagRunning} style={styles.button}>
          {isDagRunning ? 'Актуализация...' : 'Актуализировать каталог'}
        </button>
      </header>

      {error && <p style={styles.error}>{error}</p>}

      <div style={styles.grid}>
        {dataSources.length > 0 ? (
          dataSources.map(source => (
            <DataSourceCard key={source.id} source={source} onAnalyze={handleAnalyze} />
          ))
        ) : (
          <p>Источники данных не найдены. Нажмите "Актуализировать каталог", чтобы запустить профилирование.</p>
        )}
      </div>

       <footer style={styles.footer}>
        <a href="http://localhost:8080" target="_blank" rel="noreferrer">Airflow UI</a>
      </footer>
    </div>
  );
};

const styles = {
  container: { fontFamily: 'sans-serif', maxWidth: 1200, margin: '0 auto', padding: '20px' },
  header: { textAlign: 'center', marginBottom: '40px' },
  error: { color: 'red', border: '1px solid red', padding: '10px', borderRadius: '5px', textAlign: 'center' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '20px' },
  card: { border: '1px solid #e0e0e0', borderRadius: '8px', display: 'flex', flexDirection: 'column', backgroundColor: '#fff', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' },
  cardTitle: { margin: 0, padding: '15px', borderBottom: '1px solid #e0e0e0', backgroundColor: '#f9f9f9', borderTopLeftRadius: '8px', borderTopRightRadius: '8px' },
  cardBody: { padding: '15px', flexGrow: 1 },
  summarySection: { marginTop: '15px', padding: '10px', backgroundColor: '#f0f4f8', borderRadius: '5px', border: '1px solid #d9e2ec' },
  cardFooter: { padding: '15px', borderTop: '1px solid #e0e0e0', backgroundColor: '#f9f9f9', borderBottomLeftRadius: '8px', borderBottomRightRadius: '8px' },
  button: { cursor: 'pointer', padding: '8px 15px', border: 'none', borderRadius: '5px', backgroundColor: '#007bff', color: 'white' },
  footer: { textAlign: 'center', marginTop: '40px', color: '#888' },
};

export default App;
