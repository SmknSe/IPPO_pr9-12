import asyncio

import httpx


async def run_load(url: str, requests_count: int = 150) -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [client.get(f"{url}/api/rooms") for _ in range(requests_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success = sum(1 for x in results if not isinstance(x, Exception) and x.status_code < 500)
        print(f"Completed={requests_count}, success={success}")


if __name__ == "__main__":
    asyncio.run(run_load("http://myapp.local"))
