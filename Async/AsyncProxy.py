import asyncio
from datetime import datetime
import logging
from typing import Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AsyncProxyServer:
    """
        HTTP Proxy over TCP Connection
        Asyncio Implementation
    """

    chunk_limit = 1024

    def __init__(self, port: int, host: str = "localhost"):
        self.port = port
        self.host = host

    def current_time(self):
        return datetime.now().strftime("%d %b %H:%M:%S")

    def process_request(self, request: bytes)->Tuple[bytes, str, int, bytes]:
        """
            Process request to do any necessary changes
            :param request: browser request
            :return method, host, port and modified request
        """

        # downgrade HTTP 1.1 with HTTP 1.0 and change the Connection field to Close
        request = request.replace(b"HTTP/1.1", b"HTTP/1.0").replace(b"keep-alive", b"close")

        header = request.split(b'\n')[0]
        method = header.split(b' ')[0]

        if method == b'CONNECT':
            host, port = header.split(b' ')[1].split(b':')
            return method, host.decode(), int(port), request
        else:
            host_start = request.find(b'Host: ') + len(b'Host: ')
            host_end = request.find(b'\r\n', host_start)
            host_port = request[host_start: host_end].decode()

            if ':' in host_port:
                host, port = host_port.rsplit(':', 1)
                port = int(port)
            else:  # default
                host = host_port
                port = 80

            return method, host, port, request

    async def receive_all(self, reader: asyncio.StreamReader)->bytes:
        """
            To receive complete request from browser
            :param reader: To read the request
            :return: complete request
        """

        request = b''
        while True:
            try:
                chunk = await reader.read(self.chunk_limit)
                if not chunk:
                    break
                request += chunk
                if len(chunk) < self.chunk_limit:
                    break
            except Exception as e:
                logger.exception(f"Error during receiving all {e}")
                break
        return request

    async def handle_connect_request(self,
                                     browser_reader: asyncio.StreamReader,
                                     browser_writer: asyncio.StreamWriter,
                                     host: str, port: int):
        """
            To handle CONNECT Requests and create a bidirectional tunnel
            :param browser_reader: read from browser
            :param browser_writer: write to destination
            :param host: destination address
            :param port: destination port
            :return:
        """

        async def transfer(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
            """
                Helper function to link both browser & destination as a two hop TCP Connection
                :param reader: read from source
                :param writer: write to destination
                :return:
            """
            try:
                while True:
                    chunk = await reader.read(self.chunk_limit)
                    if not chunk:
                        break
                    writer.write(chunk)  # write as soon as data is arrived, saves time
                    await writer.drain()
            except Exception as e:
                logger.exception(f"{self.current_time()} Exception during transfer : {e}")
                writer.close()
                await writer.wait_closed()

        try:
            # connect to destination
            destination_reader, destination_writer = await asyncio.open_connection(host, port)

            # create bidirectional tunneling
            browser_writer.write(b"HTTP/1.0 200 Connection established\r\n\r\n")
            await browser_writer.drain()

            # run the two connections simultaneously
            await asyncio.gather(
                transfer(browser_reader, destination_writer),
                transfer(destination_reader, browser_writer)
            )
        except Exception as e:
            logging.exception(f"{self.current_time()} Exception during handling connect request : {e}")
        finally:
            # close
            destination_writer.close()
            await destination_writer.wait_closed()

    async def handle_normal_request(self,
                                    browser_writer: asyncio.StreamWriter,
                                    host: str, port: int, request: bytes):
        """
            Handle non-CONNECT requests from browser
            :param browser_writer: write from browser
            :param host: destination address
            :param port: destination port
            :param request: browser request
            :return:
        """

        try:
            # connect to destination
            destination_reader, destination_writer = await asyncio.open_connection(host, port)

            # write the request to the destination
            destination_writer.write(request)
            await destination_writer.drain()

            # read response from destination
            response = await self.receive_all(destination_reader)
            browser_writer.write(response)
            await browser_writer.drain()
        except Exception as e:
            logging.exception(f"{self.current_time()} Exception during handling normal request : {e}")
        finally:
            destination_writer.close()
            await destination_writer.wait_closed()

    async def handle_client_request(self,
                                    browser_reader: asyncio.StreamReader,
                                    browser_writer: asyncio.StreamWriter):
        """
            To handle any browser requests

            :param browser_reader: read from browser
            :param browser_writer: write to browser
            :return:
        """

        try:
            # receive request
            request = await self.receive_all(browser_reader)
            addr = browser_writer.get_extra_info('peername')
            logger.info(f"{self.current_time()} Connection Accepted at {addr}")

            # process request
            method, host, port, request = self.process_request(request)
            logger.info(f"{self.current_time()} Connection details: {method.decode('utf-8')} {host}:{port}")

            # classify request
            if method == b"CONNECT":
                await self.handle_connect_request(browser_reader, browser_writer, host, port)
            else:
                await self.handle_normal_request(browser_writer, host, port, request)
        except Exception as e:
            logging.exception(f"{self.current_time()} Exception during handling client request : {e}")
        finally:
            # close request
            browser_writer.close()
            await browser_writer.wait_closed()

    async def start_server(self):
        """
            Start the server
            :return:
        """

        self.proxy_server = await asyncio.start_server(
            self.handle_client_request,
            self.host,
            self.port
        )
        logging.info(f"{self.current_time()} Listening at {self.host}:{self.port}")
        async with self.proxy_server:
            await self.proxy_server.serve_forever()
