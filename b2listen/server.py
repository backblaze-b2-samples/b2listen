#!/usr/bin/env python3
"""
License: MIT License
Copyright (c) 2023 Miel Donkers

Very simple HTTP server in python for logging requests
Usage::
    ./server.py [<port>]

From https://gist.github.com/mdonkers/63e115cc0c79b4f6b8b3a6b797e485c7
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
from sys import argv
import logging
from threading import Thread

logging.basicConfig()
logger = logging.getLogger('b2listen.server')

DEFAULT_INTERFACE = 'localhost'
DEFAULT_PORT = 8080


class S(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        logger.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
        self._set_response()
        self.wfile.write("GET request for {}".format(self.path).encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])  # <--- Gets the size of data
        post_data = self.rfile.read(content_length)  # <--- Gets the data itself
        logger.info("POST request,\nPath: %s\nHeaders:\n%s\nBody:\n%s\n",
                    str(self.path), str(self.headers), post_data.decode('utf-8'))

        self._set_response()
        self.wfile.write("POST request for {}".format(self.path).encode('utf-8'))


class Server(Thread):
    def __init__(self, server_class=HTTPServer, handler_class=S, interface=DEFAULT_INTERFACE, port=DEFAULT_PORT,
                 daemon=False):
        super().__init__(daemon=daemon)
        server_address = (interface, port)
        self.httpd = server_class(server_address, handler_class)
        self.interface = self.httpd.server_address[0]
        self.port = self.httpd.server_address[1]

    def run(self):
        logger.info(f'Starting HTTP server on {self.interface}:{self.port}')
        try:
            self.httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        self.httpd.server_close()
        logger.info('Stopping httpd...\n')


def main():
    logger.setLevel(logging.INFO)
    if len(argv) == 2:
        arg = argv[1]
        if ':' in arg:
            [interface, port_str] = arg.split(':')
            port = int(port_str)
        else:
            interface = DEFAULT_INTERFACE
            port = int(arg)
        s = Server(port=port, interface=interface)
    else:
        s = Server()
    s.start()
    s.join()


if __name__ == '__main__':
    main()
