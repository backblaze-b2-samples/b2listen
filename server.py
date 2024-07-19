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


DEFAULT_INTERFACE = 'localhost'
DEFAULT_PORT = 8080


class S(BaseHTTPRequestHandler):
    def _set_response(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        logging.info("GET request,\nPath: %s\nHeaders:\n%s\n", str(self.path), str(self.headers))
        self._set_response()
        self.wfile.write("GET request for {}".format(self.path).encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])   # <--- Gets the size of data
        post_data = self.rfile.read(content_length)  # <--- Gets the data itself
        logging.info("POST request,\nPath: %s\nHeaders:\n%s\n\nBody:\n%s\n",
                     str(self.path), str(self.headers), post_data.decode('utf-8'))

        self._set_response()
        self.wfile.write("POST request for {}".format(self.path).encode('utf-8'))


def run(server_class=HTTPServer, handler_class=S, interface=DEFAULT_INTERFACE, port=DEFAULT_PORT):
    logging.basicConfig(level=logging.INFO)
    server_address = (interface, port)
    httpd = server_class(server_address, handler_class)
    logging.info(f'Starting httpd on {interface}:{port}...\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping httpd...\n')


def main():
    if len(argv) == 2:
        arg = argv[1]
        if ':' in arg:
            [interface, port_str] = arg.split(':')
            port = int(port_str)
        else:
            interface = DEFAULT_INTERFACE
            port = int(arg)
        run(port=port, interface=interface)
    else:
        run()


if __name__ == '__main__':
    main()
