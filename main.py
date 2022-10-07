from server import HTTPWebServer

HOST = '0.0.0.0'
PORT = 80
DEFAULT_THREAD_NUM = 256
DEFAULT_CPU_NUM = 4
DEFAULT_ROOT_DIR = './tests'


def config():
    threads = DEFAULT_THREAD_NUM
    cpus = DEFAULT_CPU_NUM
    root = DEFAULT_ROOT_DIR

    try:
        f = open('./etc/httpd.conf', 'r')
        parsedFile = f.read().split('\n')
        for text in parsedFile:
            if text.find('cpu_limit') > -1:
                cpus = int(text.split(' ')[1])
            if text.find('thread_limit') > -1:
                threads = int(text.split(' ')[1])
            if text.find('document_root') > -1:
                root = text.split(' ')[1]
        f.close()
    finally:
        return threads, cpus, root


if __name__ == '__main__':
    trds, cpus, root = config()
    server = HTTPWebServer(HOST, PORT, trds, cpus, root)
    server.listenAndServe()
