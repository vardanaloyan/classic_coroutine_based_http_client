import asyncio

import aiohttp


async def fetch_url(url, uuid):
    async with aiohttp.ClientSession() as session:
        print("[%s] Connecting to a server" % uuid)
        async with session.get(url) as response:
            print("[%s] Writing to a server" % uuid)
            result = await response.text()
            print("[%s] Reading from a server" % uuid)
            print("[%s] was completed" % uuid)
            return result


async def main():
    tasks = [
        fetch_url("https://httpbin.org/anything", "task-0"),
        fetch_url("https://httpbin.org/anything", "task-1"),
    ]
    results = await asyncio.gather(*tasks)


asyncio.run(main())
