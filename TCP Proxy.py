import socket
import threading
import datetime


f = open("blacklist.conf", "rt")
black_list = []
for name_server in f:
    black_list.append(name_server.split("\n")[0])


def get_request(conn):
    data = conn.recv(1024)
    request = b""

    if len(data) == 0:
        return b"None"

    while len(data) == 1024:
        request += data
        data = conn.recv(1024)

    request += data
    return request


def get_host(request):
    first_line = request.decode('utf-8').split('\n')[0]
    url = first_line.split(' ')[1]
    http_pos = url.find("://")
    if http_pos == -1:
        temp = url
    else:
        temp = url[(http_pos + 3):]

    port_pos = temp.find(":")

    webserver_pos = temp.find("/")
    port = -1
    if webserver_pos == -1:
        webserver_pos = len(temp)

    if (port_pos == -1 or webserver_pos < port_pos):
        port = 80
        webserver = temp[:webserver_pos]
    else:
        port = int((temp[(port_pos + 1):])[:webserver_pos - port_pos - 1])
        webserver = temp[:port_pos]

    return webserver, port


def is_blocked(web_server):
    for i in range(len(black_list)):
        if black_list[i] == web_server:
            return True

    return False


def response_403(sock, request):
    connection_socket.send(b"HTTP/1.1 403 Forbidden")
    connection_socket.close()


def create_tcp_socket():
    return socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def response_request(client_socket, sock, request):

    client_socket.send(request)

    data = client_socket.recv(1024)

    while len(data) > 0:
        sock.send(data)
        data = client_socket.recv(1024)


def print_status(time, web_server, version, response):

    if len(web_server) < 30:
        padding = ""
        for i in range(30 - len(web_server)):
            padding += " "
        print(time, "\t", web_server + padding, "\t", "HTTP/" + version[5] + version[6] + version[7], "\t", response)
    else:
        print(time, "\t", web_server[0:26] + "...", "\t\t", "HTTP/" + version[5] + version[6] + version[7],
              "\t", response)


def get_version(request):
    version = request.decode('utf-8').split("\n")[0].split(" ")[2].split("\n")[0]
    return version


def is_https(request):
    if "CONNECT" in request.decode('utf-8'):
        return True

    return False


def is_http_1_0(version):
    if "HTTP/1.0" in version:
        return True

    return False


def is_http_1_1(version):
    if "HTTP/1.1" in version:
        return True

    return False


def process_connection(connection_socket):
    try:
        time_current = datetime.datetime.now()
        time_text = time_current.time()

        request = get_request(connection_socket)

        while len(request) != 0:
            web_server, port = get_host(request)
            version = get_version(request)

            if is_https(request):
                print_status(time_text, web_server, version, "Not Supported HTTPS")
                connection_socket.close()
                return
            if is_blocked(web_server):
                response_403(connection_socket, request)
                print_status(time_text, web_server, version, "Blocked")
                connection_socket.close()
                return
            else:
                print_status(time_text, web_server, version, "OK")
                remote_server = create_tcp_socket()
                remote_server.connect((web_server, port))
                response_request(remote_server, connection_socket, request)

                remote_server.close()
                request = get_request(connection_socket)

        connection_socket.close()
    except ConnectionResetError:
        return
    except IndexError:
        return
    except OSError:
        return


server_socket = create_tcp_socket()
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
server_socket.bind(('', 8888))
server_socket.listen(50)
print("Server is running")
print("Time\t\t\t\t Host\t\t\t\t\t\t\t\t Version\t Status")

while True:
    connection_socket, connection_address = server_socket.accept()
    t = threading.Thread(target=process_connection, args=(connection_socket, ))
    t.start()
