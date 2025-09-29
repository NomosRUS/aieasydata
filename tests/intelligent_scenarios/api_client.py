import asyncio
import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class APIClient:
    """Клиент для взаимодействия с API модулей системы."""

    def __init__(self, base_urls: Dict[int, str]):
        """
        Инициализация клиента.

        Args:
            base_urls: Словарь, где ключ - номер модуля, значение - базовый URL.
        """
        self.base_urls = base_urls

    async def call(
        self,
        module: int,
        endpoint: str,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 300
    ):
        """Выполняет вызов к API модуля."""
        if module not in self.base_urls:
            logger.error(f"Module {module} not found in base_urls")
            return {"success": False, "error": f"Module {module} not configured"}

        base_url = self.base_urls.get(module, self.base_urls[0])
        
        # Правильное формирование URL с учетом модулей
        if module == 1:
            url = f"{base_url}/api/v1/data-quality{endpoint}"
        elif module == 2:
            url = f"{base_url}/api/v1/aggregation{endpoint}"
        elif module == 3:
            url = f"{base_url}/api/v1/performance{endpoint}"
        elif module == 4:
            url = f"{base_url}/api/v1/warehouse{endpoint}"
        elif module == 5:
            url = f"{base_url}/api/v1/metrics{endpoint}"
        else:
            # Для модуля 0 или общих endpoints
            url = f"{base_url}{endpoint}"
        
        # Более надежное удаление дублирования /api/v1
        # Обеспечиваем наличие слэша
        if not endpoint.startswith('/'):
            endpoint = f'/{endpoint}'

        base_url_part = base_url.split('/api/v1')[0]
        if '/api/v1/' in endpoint:
            url = f"{base_url_part}{endpoint}"
        else:
            if module == 1:
                url = f"{base_url}/api/v1/data-quality{endpoint}"
            elif module == 2:
                url = f"{base_url}/api/v1/aggregation{endpoint}"
            elif module == 3:
                url = f"{base_url}/api/v1/performance{endpoint}"
            elif module == 4:
                url = f"{base_url}/api/v1/warehouse{endpoint}"
            elif module == 5:
                url = f"{base_url}/api/v1/metrics{endpoint}"
            else:
                url = f"{base_url}{endpoint}"
        
        logger.info(f"Calling {method} {url} with params={params}, json={json_data}")
        max_retries = 3
        retry_delay = 1.0

        async with httpx.AsyncClient() as client:
            for attempt in range(max_retries + 1):
                try:
                    response = await client.request(
                        method=method.upper(),
                        url=url,
                        params=params,
                        json=json_data,
                        headers=headers,
                        timeout=timeout
                    )
                    response.raise_for_status()
                    return {"success": True, "status_code": response.status_code, "data": response.json()}
                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                    if attempt == max_retries:
                        logger.error(f"All retry attempts failed for {method} {url}")
                        if isinstance(e, httpx.HTTPStatusError):
                            return {"success": False, "error": "HTTP error", "status_code": e.response.status_code, "details": e.response.text}
                        else:
                            return {"success": False, "error": "Request error", "details": str(e)}
                    
                    wait_time = retry_delay * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                except Exception as e:
                    logger.exception("An unexpected error occurred during API call")
                    return {"success": False, "error": "Unexpected error", "details": str(e)}



