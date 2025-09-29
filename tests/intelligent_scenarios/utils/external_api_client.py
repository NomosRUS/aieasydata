import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class ExternalAPIClient:
    """Клиент для работы с внешними API в тестовых сценариях."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session = None
    
    async def _ensure_session(self):
        """Создает сессию, если она еще не существует."""
        if not self.session:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
    
    async def call_api(
        self, 
        endpoint: str, 
        method: str = "GET", 
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
        save_to: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Выполняет вызов внешнего API и сохраняет результат при необходимости.
        
        Args:
            endpoint: URL внешнего API
            method: HTTP метод (GET, POST, PUT, DELETE)
            headers: HTTP заголовки
            params: Query параметры
            payload: Тело запроса для POST/PUT
            save_to: Путь для сохранения ответа
            
        Returns:
            Dict с результатом вызова API
        """
        await self._ensure_session()
        
        try:
            logger.info(f"Calling external API: {method} {endpoint}")
            
            # Подготовка параметров запроса
            kwargs = {
                "url": endpoint,
                "headers": headers or {},
                "params": params
            }
            
            if method.upper() in ["POST", "PUT", "PATCH"] and payload:
                kwargs["json"] = payload
            
            # Выполнение запроса
            async with self.session.request(method.upper(), **kwargs) as response:
                response_text = await response.text()
                
                # Попытка парсинга JSON
                try:
                    response_data = json.loads(response_text)
                except json.JSONDecodeError:
                    response_data = {"raw_text": response_text}
                
                result = {
                    "success": response.status < 400,
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "data": response_data
                }
                
                # Сохранение ответа в файл, если указан путь
                if save_to and result["success"]:
                    await self._save_response(save_to, response_data)
                    result["saved_to"] = save_to
                
                logger.info(f"External API call completed: {response.status}")
                return result
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout calling external API: {endpoint}")
            return {
                "success": False,
                "error": "Timeout",
                "status_code": 408
            }
        except Exception as e:
            logger.error(f"Error calling external API {endpoint}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "status_code": 500
            }
    
    async def close(self):
        """Закрывает HTTP сессию."""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def _save_response(self, file_path: str, data: Any):
        """Сохраняет ответ API в файл."""
        try:
            # Создание директории если не существует
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Сохранение данных
            with open(path, 'w', encoding='utf-8') as f:
                if isinstance(data, (dict, list)):
                    json.dump(data, f, ensure_ascii=False, indent=2)
                else:
                    f.write(str(data))
            
            logger.info(f"Response saved to: {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save response to {file_path}: {str(e)}")
            raise

# Синхронная обертка для совместимости
class SyncExternalAPIClient:
    """Синхронная версия клиента для простого использования."""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
    
    def call_api(self, *args, **kwargs) -> Dict[str, Any]:
        """Синхронная версия вызова API."""
        async def _call():
            async with ExternalAPIClient(self.timeout) as client:
                return await client.call_api(*args, **kwargs)
        
        return asyncio.run(_call())
