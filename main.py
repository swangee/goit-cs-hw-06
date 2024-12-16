import asyncio
import datetime
import json
import logging
import mimetypes
import os
import pathlib
import threading
import urllib
from http.server import BaseHTTPRequestHandler, HTTPServer
from pymongo import MongoClient
import websockets


logging.basicConfig(level=logging.INFO)

class SocketServer:
    __db: MongoClient = None

    def __init__(self, db):
        self.__db = db

    async def ws_handler(self, ws):
        while True:
            message = await ws.recv()
            self.__handle_message(message)

    def __handle_message(self, message_str):
        message = json.loads(message_str)

        entry = {"date": str(datetime.datetime.now())}
        entry["username"] = message["username"]
        entry["message"] = message["message"]

        self.__db["goit"]["messages"].insert_one(entry)

class HttpHandler(BaseHTTPRequestHandler):
    static_path = "http"

    def do_GET(self):
        pr_url = urllib.parse.urlparse(self.path)
        if pr_url.path == '/':
            self.send_html_file(self.__make_file_name('index.html'))
        elif pr_url.path == '/message.html':
            self.send_html_file(self.__make_file_name('message.html'))
        else:
            if pathlib.Path().joinpath(self.__make_file_name(pr_url.path[1:])).exists():
                self.send_static()
            else:
                self.send_html_file(self.__make_file_name('error.html'), 404)

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_static(self):
        self.send_response(200)
        file_path = self.__make_file_name(self.path.strip('/'))
        mt = mimetypes.guess_type(file_path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()
        with open(f'{file_path}', 'rb') as file:
            self.wfile.write(file.read())

    def __make_file_name(self, filename):
        cwd = os.getcwd()
        file_path = os.path.join(cwd, self.static_path, filename)
        return file_path

def run_http_server(server_class=HTTPServer, handler_class=HttpHandler):
    server_address = ('', 3000)
    http = server_class(server_address, handler_class)
    try:
        logging.info(f'Starting HTTP server on {server_address}')
        http.serve_forever()
    except KeyboardInterrupt:
        http.server_close()


async def do_run_ws_server(mongo_client):
    server = SocketServer(mongo_client)
    async with websockets.serve(server.ws_handler, '0.0.0.0', 5000):
        await asyncio.Future()# run forever

def run_ws_server(mongo_client):
    asyncio.run(do_run_ws_server(mongo_client))

def main():
    mongo_client = MongoClient(os.getenv('MONGO_DSN'))

    # Запуск потоків для прослуховування та письма
    http_server_thread = threading.Thread(target=run_http_server)
    http_server_thread.start()

    ws_server_thread = threading.Thread(target=run_ws_server, args=(mongo_client,))
    ws_server_thread.start()

    http_server_thread.join()
    ws_server_thread.join()

    mongo_client.close()


if __name__ == '__main__':
    main()