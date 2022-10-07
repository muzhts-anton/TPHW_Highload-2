from datetime import datetime
from urllib.parse import unquote
from urllib.parse import urlparse
import mimetypes
import threading
import os
import queue
import socket
import signal


BAD_REQ_HDR = [('Server', 'Python-thread-pool-server'),
               ('Date', datetime.now()),
               ('Connection', 'close')]


class HTTPResponse:
    def __init__(self, code, status, headers=None, body=None):
        self.code = code
        self.status = status
        self.hdr = headers
        self.body = body


class HTTPRequest:
    def __init__(self, method, path, headers, body):
        self.method = method
        self.url = urlparse(path).path
        self.hdr = headers
        self.body = body


class HTTPWebServer():
    def __init__(self, host, port, threads, cpus, dir):
        self.cpunum = cpus
        self.host = host
        self.port = port
        self.trd = threads
        self.root = dir
        self.pids = []
        self.reqq = queue.SimpleQueue()

    def threadWork(self):
        while True:
            conn = self.reqq.get()
            if conn:
                self.handle(conn)
                conn.close()

    def listenAndServe(self):
        print('> BEGIN')
        print(f'> config\n\t* cpu: {self.cpunum}\n\t* thread: {self.trd}')

        sock = socket.socket()
        try:
            sock.bind((self.host, self.port))
            sock.listen()
            pid = 0
            print('pids:')
            for _ in range(self.cpunum):
                pid = os.fork()
                if pid == 0:
                    continue
                for _ in range(self.trd):
                    t = threading.Thread(target=self.threadWork, daemon=True)
                    t.start()
                self.pids.append(pid)
                print(f'\t{pid}')
                while True:
                    conn, _ = sock.accept()
                    self.reqq.put(conn)

            while True:
                1  # отвисаем

        except KeyboardInterrupt:
            sock.close()
            for pid in self.pids:
                os.kill(pid, signal.SIGTERM)
            print('')

    def handle(self, conn):
        request = self.parseRequest(conn)
        if (type(request) != HTTPRequest):
            self.response(conn, request)
            return
        if request.url.find('/../') != -1:
            self.response(conn, HTTPResponse(403, 'Forbidden', BAD_REQ_HDR))
            return
        indexFile = False
        unquotedPath = unquote(request.url)
        if request.url[-1] == '/' and request.url.find('.') == -1:
            filePath = self.root + unquotedPath + 'index.html'
            indexFile = True
        else:
            filePath = self.root + unquotedPath

        try:
            file = open(filePath, 'rb')
        except:
            if indexFile:
                resp = HTTPResponse(403, 'Forbidden', BAD_REQ_HDR)
            else:
                resp = HTTPResponse(404, 'Not Found', BAD_REQ_HDR)
            self.response(conn, resp)
            return

        t, _ = mimetypes.guess_type(filePath, strict=True)
        headers = [('Content-Type', t),
                   ('Content-Length', os.path.getsize(filePath)),
                   ('Server', 'Python-thread-pool-server'),
                   ('Date', datetime.now()),
                   ('Connection', 'close')]
        self.response(conn, HTTPResponse(200, 'OK', headers))

        if request.method == 'GET':
            conn.sendfile(file)
        file.close()

    def response(self, conn, res):
        answer = conn.makefile('w')
        answer.write(f'HTTP/1.1 {res.code} {res.status}\r\n')

        if res.hdr:
            for (key, value) in res.hdr:
                answer.write(f'{key}: {value}\r\n')
        answer.write('\r\n')

        if res.body:
            answer.write(res.body)
        answer.close()

    def parseRequest(self, conn):
        rawFile = conn.makefile('r')
        info = rawFile.readline().split()
        if len(info) != 3:
            return HTTPResponse(400, 'Bad request', BAD_REQ_HDR)
        method, path, ver = info
        if method != 'GET' and method != 'HEAD':
            return HTTPResponse(405, 'Method Not Allowed', BAD_REQ_HDR)
        if ver != 'HTTP/1.1' and ver != 'HTTP/1.0':
            return HTTPResponse(505, 'HTTP Version Not Supported', BAD_REQ_HDR)
        headers = {}
        while True:
            line = rawFile.readline()
            if line in ('\r\n', '\n', ''):
                break
            headerName, headerValue = line.split(':')
            headers[headerName] = headerValue
        if 'Content-length' in headers:
            req = HTTPRequest(method, path, headers,
                              rawFile.read(int(headers['Content-length'])))
            rawFile.close()
            return req
        else:
            rawFile.close()
            return HTTPRequest(method, path, headers, None)
