import socket
import time

PROXY_HOST = "127.0.0.1"
PROXY_PORT = 8080


def send_get_request(url):
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((PROXY_HOST, PROXY_PORT))

        request = (
            f"GET {url} HTTP/1.1\r\n"
            f"Host: proxy\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        )

        start_time = time.time()

        client_socket.sendall(request.encode())

        response = b""

        while True:
            data = client_socket.recv(4096)
            if not data:
                break
            response += data

        end_time = time.time()
        response_time = end_time - start_time

        decoded_response = response.decode(errors="ignore")

        print("\n========== HTTP RESPONSE ==========")
        print(decoded_response[:2000])

        print("\n========== PERFORMANCE ==========")
        print(f"Response time: {response_time:.4f} seconds")

        if "X-Cache: MISS" in decoded_response:
            print("Result: Fetched from external web server (Cache Miss)")
        elif "X-Cache: HIT" in decoded_response:
            print("Result: Served from cache (Cache Hit)")
        elif "X-Cache: BLOCKED" in decoded_response:
            print("Result: Blocked by firewall")
        elif "400 Bad Request" in decoded_response:
            print("Result: Invalid request handled by exception handling")
        elif "404 Not Found" in decoded_response:
            print("Result: Network/DNS error handled by exception handling")
        elif "504 Gateway Timeout" in decoded_response:
            print("Result: Timeout handled by exception handling")
        else:
            print("Result: Response received")

        client_socket.close()

    except ConnectionRefusedError:
        print("Error: Proxy server is not running.")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    while True:
        print("\nHTTP Proxy Client")
        print("Example: http://example.com")
        print("Type 'exit' to stop.")

        url = input("Enter URL: ").strip()

        if url.lower() == "exit":
            break

        send_get_request(url)
