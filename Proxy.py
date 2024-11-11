import socket
import sys
import threading
from datetime import datetime


class ProxyServer:
    def __init__(self, port_num):
        self.port = port_num
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # TCP connection
        self.server.bind(('localhost', self.port))
        self.server.listen(10)
        print(f">>> {self.current_time()} - Proxy server listening on port {self.port}")

    def accept_client_request(self):
        while True:
            client_socket, addr = self.server.accept()  # accept connection from client (client initiates a request to a destination)
            print(f">>> {self.current_time()} Accepted connection from {addr[0]}:{addr[1]}")  # web browser address
            client_handler = threading.Thread(target=self.handle_client_request, args=(client_socket,))
            client_handler.start()

    def handle_client_request(self, client_socket):
        request = self.receive_all(client_socket)  # receive requests from the client

        try:
            method, host, port = self.process_request(request)  # get method, host, port details of destination
            print(f">>> {self.current_time()} - {method.decode('utf-8')} {host} {port}")

            if method == b"CONNECT":  # Create a HTTP Tunnel
                self.handle_connect_request(client_socket, host, port)
            else:
                self.handle_normal_request(client_socket, host, port, request)
        except Exception as e:
            print(f"Error Client Request {e}")
        finally:
            client_socket.close()

    def handle_connect_request(self, client_socket, host, port):
        def forward_data(client_socket, destination_socket):
            def forward(source, destination):  # two hop TCP connection
                try:
                    while True:
                        data = source.recv(1024)
                        if not data:
                            break
                        destination.sendall(data)
                except:
                    pass
                finally:
                    source.close()
                    destination.close()

            # The tunnel is created each time a message is sent between the client and destination
            client_to_server = threading.Thread(target=forward, args=(client_socket, destination_socket))
            server_to_client = threading.Thread(target=forward, args=(destination_socket, client_socket))
            client_to_server.start()
            server_to_client.start()
            client_to_server.join()
            server_to_client.join()

        try:
            destination_socket = socket.create_connection((host, port))
            client_socket.sendall(b"HTTP/1.0 200 Connection established\r\n\r\n")
            forward_data(client_socket, destination_socket)
        except Exception as e:
            print(f"Error HTTPS {e}")

    def handle_normal_request(self, client_socket, host, port, request):
        try:
            destination_socket = socket.create_connection((host, port))
            destination_socket.sendall(request)

            response = self.receive_all(destination_socket)
            client_socket.sendall(response)

            destination_socket.close()  # close the connection after message is sent
        except Exception as e:
            print(f"Error HTTP {e}")

    def process_request(self, request):
        # downgrade to HTTP 1.0 & close connections
        request = request.replace(b"HTTP/1.1", b"HTTP/1.0").replace(b"keep-alive", b"close")

        header = request.split(b'\n')[0]
        method = header.split(b' ')[0]  # GET, CONNECT, PUT, POST
        if method == b'CONNECT':
            print(header.decode())
            host_port = header.split(b' ')[1]
            host, port = host_port.split(b':')
            return method, host.decode(), int(port)
		
        # Get host and port number from request
        host_start = request.find(b'Host: ') + len('Host: ')
        host_end = request.find(b'\r\n', host_start)
        host_port = request[host_start:host_end].decode()

        if ':' in host_port:
            host, port = host_port.rsplit(':', 1)
            port = int(port)
        else:  # default
            host = host_port
            port = 80

        return method, host, port

    def receive_all(self, sock):  # receive function
        data = b''
        while True:
            part = sock.recv(1024)
            data += part
            if len(part) < 1024:
                break
        return data

    def current_time(self):
        return datetime.now().strftime("%d %b %H:%M:%S")


# To call
# proxy = ProxyServer(port_num)
# proxy.accept_client_request()
