import asyncio
import sys
import httpx
import time

async def run_load(url: str, requests_count: int = 150, concurrency: int = 10) -> None:
    """Отправляет запросы с контролем конкурентности"""
    
    async def send_request(client, url, semaphore):
        async with semaphore:  # Ограничиваем количество одновременных запросов
            try:
                response = await client.get(
                    f"{url}/api/rooms",
                    headers={"Host": "myapp.local"},
                    timeout=5.0
                )
                return response if response.status_code < 500 else None
            except Exception as e:
                return None
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        semaphore = asyncio.Semaphore(concurrency)  # Не более concurrency запросов одновременно
        
        tasks = [
            send_request(client, url, semaphore) 
            for _ in range(requests_count)
        ]
        
        print(f"Отправка {requests_count} запросов (максимум {concurrency} одновременно)...")
        results = await asyncio.gather(*tasks)
        
        success = sum(1 for r in results if r is not None)
        print(f"Completed={requests_count}, success={success}")

if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1"
    asyncio.run(run_load(base_url, concurrency=10))  # ← Не больше 10 запросов одновременно
