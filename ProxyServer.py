import socket
from urllib.parse import urlparse

PROXY_HOST = "127.0.0.1"
PROXY_PORT = 8080

cache = {}

blocked_domains = [
    "facebook.com",
    "youtube.com",
    "example-blocked.com"
]


def is_blocked(host):
    for domain in blocked_domains:
        if domain in host:
            return True
    return False


def build_response(status_code, status_text, body, cache_status="NONE"):
    body_bytes = body.encode("utf-8")

    response = (
        f"HTTP/1.1 {status_code} {status_text}\r\n"
        f"Content-Type: text/html; charset=UTF-8\r\n"
        f"Content-Length: {len(body_bytes)}\r\n"
        f"X-Cache: {cache_status}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    ).encode("utf-8") + body_bytes

    return response


def fetch_from_web(url):
    parsed_url = urlparse(url)

    host = parsed_url.hostname
    path = parsed_url.path

    if path == "":
        path = "/"

    if parsed_url.query:
        path += "?" + parsed_url.query

    web_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    web_socket.settimeout(10)

    web_socket.connect((host, 80))

    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    )

    web_socket.sendall(request.encode())

    response = b""

    while True:
        data = web_socket.recv(4096)
        if not data:
            break
        response += data

    web_socket.close()
    return response


def handle_client(client_socket):
    try:
        request = client_socket.recv(4096).decode(errors="ignore")

        if not request:
            return

        first_line = request.split("\r\n")[0]
        parts = first_line.split()

        if len(parts) < 2 or parts[0] != "GET":
            print("[EXCEPTION] Invalid request format")

            response = build_response(
                400,
                "Bad Request",
                "<h1>400 Bad Request</h1><p>Only HTTP GET requests are supported.</p>"
            )
            client_socket.sendall(response)
            return

        url = parts[1].strip()
        parsed_url = urlparse(url)

        if parsed_url.scheme != "http" or parsed_url.hostname is None:
            print("[EXCEPTION] Invalid URL entered by client")

            response = build_response(
                400,
                "Bad Request",
                "<h1>400 Bad Request</h1><p>Please use a full HTTP URL, such as http://example.com</p>"
            )
            client_socket.sendall(response)
            return

        host = parsed_url.hostname

        if is_blocked(host):
            print(f"[FIREWALL] Blocked request to: {host}")

            response = build_response(
                403,
                "Forbidden",
                f"<h1>403 Forbidden</h1><p>Access to {host} is blocked by the proxy firewall.</p>",
                "BLOCKED"
            )
            client_socket.sendall(response)
            return

        if url in cache:
            print(f"[CACHE HIT] Served from cache: {url}")

            cached_response = cache[url].replace(
                b"X-Cache: MISS",
                b"X-Cache: HIT"
            )

            client_socket.sendall(cached_response)
            return

        print(f"[CACHE MISS] Fetching from web server: {url}")

        response = fetch_from_web(url)

        response = response.replace(
            b"\r\n\r\n",
            b"\r\nX-Cache: MISS\r\n\r\n",
            1
        )

        cache[url] = response

        client_socket.sendall(response)

    except socket.gaierror as e:
        print(f"[EXCEPTION] DNS Error: {e}")

        response = build_response(
            404,
            "Not Found",
            "<h1>404 Not Found</h1><p>The requested web server could not be found.</p>"
        )
        client_socket.sendall(response)

    except socket.timeout as e:
        print(f"[EXCEPTION] Timeout Error: {e}")

        response = build_response(
            504,
            "Gateway Timeout",
            "<h1>504 Gateway Timeout</h1><p>The external web server did not respond in time.</p>"
        )
        client_socket.sendall(response)

    except Exception as e:
        print(f"[EXCEPTION] General Error: {e}")

        response = build_response(
            500,
            "Internal Server Error",
            f"<h1>500 Internal Server Error</h1><p>{str(e)}</p>"
        )
        client_socket.sendall(response)

    finally:
        client_socket.close()


def start_proxy():
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    proxy_socket.bind((PROXY_HOST, PROXY_PORT))
    proxy_socket.listen(5)

    print(f"Proxy server running on {PROXY_HOST}:{PROXY_PORT}")
    print("Waiting for client requests...")

    while True:
        client_socket, client_address = proxy_socket.accept()
        print(f"\n[NEW REQUEST] From client: {client_address}")
        handle_client(client_socket)


if __name__ == "__main__":
    start_proxy()
