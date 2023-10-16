import asyncio
import logging
import urllib.parse

LOG_LEVEL = "INFO"  # Log level for the logger
logging.basicConfig(level=LOG_LEVEL, format="%(message)s")  # Configure the logger
logger = logging.getLogger("AsyncioApp")  # Create a logger object

async def read(reader, uuid):
    logger.info("[%s] Reading from a server", uuid)
    result = ""
    while True:
        line = await reader.readline()
        if not line:
            break

        line = line.decode("latin1").rstrip()
        if line:
            result += line
    return result


async def http_get(url, uuid):
    url = urllib.parse.urlsplit(url)
    logger.info("[%s] Connecting to a server", uuid)

    reader, writer = await asyncio.open_connection(url.hostname, 80)  # Connect to a server

    query = f"GET {url.path or '/'} HTTP/1.0\r\n" f"Host: {url.hostname}\r\n" f"\r\n"
    logger.info("[%s] Writing to a server", uuid)
    writer.write(query.encode("latin-1")) # Write to a server

    response = await read(reader, uuid) # Read from a server
    logger.info("[%s] was completed", uuid)
    
    return response


async def main():
    url = "https://httpbin.org/anything"
    tasks = [
        http_get(url, "task-0"),
        http_get(url, "task-1"),
    ]
    results = await asyncio.gather(*tasks)
    # print(results[0])

asyncio.run(main())
