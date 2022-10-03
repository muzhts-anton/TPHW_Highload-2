from datetime import datetime
from urllib.parse import unquote
from urllib.parse import urlparse
import mimetypes
import threading
import os
import queue
import socket
import signal


class HTTPResponse:
    def __init__(self, code, status, headers=None, body=None):
        self._code = code
        self._status = status
        self._headers = headers
        self._body = body


class HTTPRequest:
    def __init__(self, method, path, ver, headers, body):
        self._method = method
        self._path = urlparse(path).path
        self._ver = ver
        self._headers = headers
        self._body = body


class HTTPWebServer():
    def __init__(self, host, port, threads, dir):
        self._cpuNum = os.cpu_count()
        self._host = host
        self._port = port
        self._threads = threads
        self._dir = dir
        self._cpuPool = []
        self._requestQueue = queue.SimpleQueue()
        self._badReqHeaders = [('Server', 'Python-thread-pool-server'),
                               ('Date', datetime.now()),
                               ('Connection', 'close')]

    def listenAndServe(self):
        sock = socket.socket()
        try:
            sock.bind((self._host, self._port))
            sock.listen()
            pid = 0
            for _ in range(self._cpuNum):
                pid = os.fork()
                if pid == 0:
                    continue
                for _ in range(self._threads):
                    t = threading.Thread(target=self.threadWork, daemon=True)
                    t.start()
                self._cpuPool.append(pid)
                print(pid)
                while True:
                    conn, _ = sock.accept()
                    self._requestQueue.put(conn)

            while True:
                1 # отвисаем

        except KeyboardInterrupt:
            sock.close()
            for pid in self._cpuPool:
                os.kill(pid, signal.SIGTERM)

    def threadWork(self):
        while True:
            conn = self._requestQueue.get()
            if conn:
                self.handle(conn)
                conn.close()

    def fileLookUp(self, conn, filePath):
        type, _ = mimetypes.guess_type(filePath, strict=True)
        headers = [('Content-Type', type),
                   ('Content-Length', os.path.getsize(filePath)),
                   ('Server', 'Python-thread-pool-server'),
                   ('Date', datetime.now()),
                   ('Connection', 'close')]
        self.response(conn, HTTPResponse(200, 'OK', headers))

    def handle(self, conn):
        request = self.parseRequest(conn)
        if (type(request) != HTTPRequest):
            # отправляем ошибкой, если произошла ошибка парсинга
            self.response(conn, request)
            return
        if request._path.find('/../') != -1:
            self.response(conn,
                          HTTPResponse(403, 'Forbidden', self._badReqHeaders))
            return
        indexFile = False
        unquotedPath = unquote(request._path)
        if request._path[-1] == '/' and request._path.find('.') == -1:
            filePath = self._dir + unquotedPath + 'index.html'
            indexFile = True
        else:
            filePath = self._dir + unquotedPath

        try:
            file = open(filePath, 'rb')
        except:
            if indexFile:
                resp = HTTPResponse(
                    403, 'Forbidden', headers=self._badReqHeaders)
            else:
                resp = HTTPResponse(
                    404, 'Not Found', headers=self._badReqHeaders)
            self.response(conn, resp)
            return

        self.fileLookUp(conn, filePath)
        if request._method == 'GET':
            try:
                conn.sendfile(file)
            except BrokenPipeError:
                conn.sendfile(file)
        file.close()

    def response(self, conn, res):
        answer = conn.makefile('w')
        answer.write(f'HTTP/1.1 {res._code} {res._status}\r\n')

        if res._headers:
            for (key, value) in res._headers:
                answer.write(f'{key}: {value}\r\n')
        answer.write('\r\n')

        if res._body:
            answer.write(res.body)
        answer.close()

    def parseRequest(self, conn):
        rawFile = conn.makefile('r')
        info = rawFile.readline().split()
        if len(info) != 3:
            return HTTPResponse(400, 'Bad request', self._badReqHeaders)
        method, path, ver = info
        if method != 'GET' and method != 'HEAD':
            return HTTPResponse(405, 'Method Not Allowed', self._badReqHeaders)
        if ver != 'HTTP/1.1' and ver != 'HTTP/1.0':
            return HTTPResponse(505, 'HTTP Version Not Supported', self._badReqHeaders)
        headers = {}
        while True:
            line = rawFile.readline()
            if line in ('\r\n', '\n', ''):
                break
            headerName, headerValue = line.split(':')
            headers[headerName] = headerValue
        if 'Content-length' in headers:
            req = HTTPRequest(method, path, ver, headers,
                              rawFile.read(int(headers['Content-length'])))
            rawFile.close()
            return req
        else:
            rawFile.close()
            return HTTPRequest(method, path, ver, headers, None)
