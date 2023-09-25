import json  # Used to parse the response body
import logging  # Used to log the output
import selectors  # Cross platform networking library. Used to wait for events on sockets. Used in event loop.
import socket  # Low level networking library. Used to create sockets.
import urllib.parse  # Used to parse the URL, i.e. scheme, netloc, path, etc.
from collections import namedtuple  # Used to store the response body and headers

LOG_LEVEL = "INFO"  # Log level for the logger
logging.basicConfig(level=LOG_LEVEL, format="%(message)s")  # Configure the logger
selector = selectors.DefaultSelector()  # Create a selector object

logger = logging.getLogger("ConcurrentApp")  # Create a logger object
Response = namedtuple(
    "Response", ["body", "headers"]
)  # Create a named tuple to store the response body and headers


def connect(sock, url, _uuid):
    """Function to connect to a server

    Args:
        sock (socket): Socket object
        url (SplitResultBytes): URL object, parsed using urllib.parse.urlsplit
        _uuid (str): UUID of the task
    """
    logger.info("[%s] Connecting to a server", _uuid)
    try:
        sock.connect((url.netloc, 80))
    except BlockingIOError:
        pass


def write(url, _uuid):
    """Function to write to a server

    Args:
        url (SplitResultBytes): URL object, parsed using urllib.parse.urlsplit
        _uuid (str): UUID of the task
    """
    sock = yield
    logger.info("[%s] Writing to a server", _uuid)
    http_request = f"GET {url.path} HTTP/1.1\r\nHost: {url.netloc}\r\n\r\n"
    sock.sendall(http_request.encode())
    selector.modify(sock, selectors.EVENT_READ, _uuid)


def read(_uuid):
    """Function to read from a server

    Args:
        _uuid (str): UUID of the task

    Returns:
        Response (namedtuple): namedtuple containing the response body and headers
    """
    headers = b""
    body = b""
    headers_parsed = False
    sock = yield

    logger.info("[%s] Reading from a server", _uuid)

    while True:
        try:
            data = sock.recv(512)
        except BlockingIOError:
            continue

        if not data:
            selector.unregister(sock)
            sock.close()
            break

        if not headers_parsed:
            headers += data

            if b"\r\n\r\n" in headers:
                headers, rest = headers.split(b"\r\n\r\n", 1)
                headers_parsed = True

                for line in headers.split(b"\r\n"):
                    if line.startswith(b"Content-Length:"):
                        content_length = int(line.split(b":")[1].strip())
                        break
                body += rest
        else:
            body += data
            if content_length is not None and len(body) >= content_length:
                break
    sock.close()
    return Response(json.loads(body), headers.decode())


def http_get(url):
    """Function to fetch a URL. It binds the connect, write and read functions together.

    Args:
        url (str): URL to fetch

    Returns:
        Response (namedtuple): namedtuple containing the response body and headers

    Yields:
        _uuid (str): UUID of the task
    """
    _uuid = yield
    url_info = urllib.parse.urlsplit(url)
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_sock.setblocking(False)
    selector.register(client_sock, selectors.EVENT_WRITE, _uuid)
    connect(client_sock, url_info, _uuid)

    yield from write(url_info, _uuid)
    result = yield from read(_uuid)
    return result


def event_loop(tasks):
    """Function to run the event loop

    Args:
        tasks (list): List of tasks to run

    Returns:
        list: List of results from the tasks
    """
    tasks_dict = {}
    results_dict = {}

    logger.debug("[eventloop] Adding %s tasks to eventloop.", len(tasks))

    for _index, _task in enumerate(tasks):
        _uuid = f"task-{_index}"
        _task.send(None)  # Prime/Advance the generator
        _task.send(_uuid)  # Send the UUID to the generator
        tasks_dict[_uuid] = _task

    try:
        while tasks_dict:
            logger.debug("[eventloop] Waiting for an event...")
            events = selector.select()
            logger.debug("[eventloop] Got %d event", len(events))
            for key, mask in events:
                read_event = mask & selectors.EVENT_READ
                event_type = "READ" if read_event else "WRITE"
                _uuid = key.data
                logger.debug("[eventloop] [%s] New '%s' event", _uuid, event_type)
                task = tasks_dict.pop(_uuid)
                try:
                    task.send(key.fileobj)
                    tasks_dict[_uuid] = task
                except StopIteration as e:
                    results_dict[_uuid] = e.value
                    logger.info("[eventloop] [%s] was completed", _uuid)
        logger.debug("[eventloop] Exiting. All tasks are completed")
    finally:
        selector.close()
        return list(results_dict.values())


tasks = [
    http_get("https://httpbin.org/anything"),
    http_get("https://httpbin.org/anything"),
]
results = event_loop(tasks)
# for _ind, result in enumerate(results):
#     logger.debug("Body %d: %s", _ind, json.dumps(result.body, indent=2))
#     logger.debug("Header %d: %s", _ind, result.headers)
