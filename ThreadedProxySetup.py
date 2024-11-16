#!/usr/bin/env python3

from ThreadedProxy import *
import sys

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <server-address> <server-port>")
        sys.exit(1)

    server_address = sys.argv[1]
    server_port = int(sys.argv[2])
    ThreadedProxyServer(server_port, server_address).accept_client_request()
