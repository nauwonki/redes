import socket 
import json
import sys

#Parsear mensaje HTTP
def parse_HTTP_message(http_message: bytes):
    #Separar Head y Body spliteando en \r\n\r\n
    separate = http_message.split(b"\r\n\r\n")
    #Definir Head y Body, decodificando el head
    head = separate[0].decode()
    body = separate[1]

    #Separar los headers y definir el start line
    header = head.split("\r\n")
    start_line = header[0]

    #Parsear start line
    start_line_parts = start_line.split(" ", 2)
    message = None
    start_line_parsed = {}

    if (start_line_parts[0].startswith("HTTP/")):
        #Es un response
        message = "Response"
        start_line_parsed["version"] = start_line_parts[0]
        start_line_parsed["codigo"] = start_line_parts[1]
        start_line_parsed["texto"] = start_line_parts[2]
    else:
        #Es un request
        message = "Request"
        start_line_parsed["metodo"] = start_line_parts[0]
        start_line_parsed["direccion"] = start_line_parts[1]
        start_line_parsed["version"] = start_line_parts[2]

    #Headers restantes
    headers = [line for line in header[1:] if line]

    return {
        "tipo": message,
        "start_line": start_line_parsed,
        "headers": headers,
        "body": body
    }


def create_HTTP_message(parsed_message):
    #Identificar startline, headers y body
    start_line_parsed = parsed_message["start_line"]
    headers = parsed_message["headers"]
    body = parsed_message["body"]

    #Identificar starline dependiendo del tipo del mensaje
    if parsed_message["tipo"] == "Request":
        start_line = f"{start_line_parsed['metodo']} {start_line_parsed['direccion']} {start_line_parsed['version']}"
    else:
        start_line = f"{start_line_parsed['version']} {start_line_parsed['codigo']} {start_line_parsed['texto']}"

    body_to_bytes = body

    #Construir headers
    header_lines = [start_line]
    for h in headers:
        header_lines.append(h)

    #Unir head y pasar a bytes
    head_to_bytes = ("\r\n".join(header_lines) + "\r\n\r\n").encode()

    #Unir head y body
    return head_to_bytes + body_to_bytes


#Socket servidor tcp
#Analogo al tcp_socket_server.py de EOL pero los decodes ya se hacen en parse HTTP
#y sin remove_end_of_message porque queremos diferenciar \r\n\r\n
def receive_full_message(connection_socket, buff_size, end_sequence):
    recv_message = connection_socket.recv(buff_size)
    full_message = recv_message

    is_end_of_message = contains_end_of_message(full_message, end_sequence)

    while not is_end_of_message and len(recv_message) > 0:
        recv_message = connection_socket.recv(buff_size)

        full_message += recv_message

        is_end_of_message = contains_end_of_message(full_message, end_sequence)

    return full_message

def contains_end_of_message(message, end_sequence):
    return end_sequence in message

def get_destination(parsed_request):
    host = None
    port = 80

    for h in parsed_request["headers"]:
        if h.lower().startswith("host:"):
            host_val = h.split(":", 1)[1].strip()
            if ":" in host_val:
                host, port_str = host_val.split(":")
                port = int(port_str)
            else:
                host = host_val
            break
    return host, port

def receive_until_close(connection_socket, buff_size):
    full_message = b""
    connection_socket.settimeout(2.0)
    try:
        while True:
            c = connection_socket.recv(buff_size)
            if len(c) == 0:
                break
            full_message += c
    except socket.timeout:
        pass
    return full_message

def load_blocked_sites(filename="config.json"):
    block = []
    with open(filename, "r") as f:
        c = f.read()
        if "blocked" in c:
            separate_block = c.split('"blocked"', 1)[1].split("]", 1)[0]
            i = separate_block.split("[", 1)[-1].split(",")
            for item in i:
                stripped = item.strip().strip('""').strip("'").strip()
                if stripped:
                    block.append(stripped)
    return block

def is_blocked(parsed_request, blocked):
    host, _ = get_destination(parsed_request)
    path = parsed_request["start_line"].get("direccion", "")
    url = f"{host}{path}" if host else path

    for b in blocked:
        c = b.replace("http://", "")
        if c in url or (host and c in host):
            return True
    return False

def response_403():
    html = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>403 Forbidden</title>
</head>
<body>
    <h1>403 Forbidden - Acceso Denegado</h1>
    <p>El sitio web al que intentas acceder está bloqueado por el Proxy.</p>
    <img src="/gato.jpg" alt="Sitio Bloqueado">
</body>
</html>"""
    body = html.encode()
    res = [
        "HTTP/1.1 403 Forbidden",
        "Content-Type: text/html",
        f"Content-length: {len(body)}"
        "Connection: close"
    ]
    headers = "\r\n".join(res) + "\r\n\r\n"
    return headers.encode() + body

def build_image(image="gato.jpg"):
    with open(image, "rb") as f:
        image_byte = f.read()
    res = [
        "HTTP/1.1 200 OK",
        "Content-Type: image/jpeg",
        f"Content-Length: {len(image_byte)}",
        "Connection: close"
    ]
    headers = "\r\n".join(res) + "\r\n\r\n"
    return headers.encode() + image_byte

#Se obtiene ruta del archivo recibido
#config_route = sys.argv[1]

#Abrimos el archivo del config
#with open(config_route) as file:
    #data = json.load(file)
    #name = data['usuario']['nombre']


if __name__ == "__main__":
    blocked = load_blocked_sites("config.json")
    buff_size = 4096
    end_of_message = b"\r\n\r\n"
    new_socket_address = ('127.0.0.1', 8000)

    print('Creando socket - Proxy')
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server_socket.bind(new_socket_address)
    server_socket.listen(5)

    print('... Esperando clientes')
    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Conexion desde: {client_address}")
        client_request = receive_full_message(client_socket, buff_size, end_of_message)

        #print("Request recibida")
        #print(recv_message)

        if len(client_request) > 0:
            print("ejecutando parse HTTP")
            #Al recibir mensaje, parsearlo
            parsed_request = parse_HTTP_message(client_request)
            path = parsed_request["start_line"].get("direccion", "")
            
            if path.endswith("gato.jpg"):
                print("peticion recibida imagen gato")
                client_socket.send(build_image("gato.jpg"))
            elif is_blocked(parsed_request, blocked):
                print("sitio bloqueado")
                client_socket.send(response_403())
            else:
                host, port = get_destination(parsed_request)
                print(f"destino: {host}:{port}")

                dest_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                
                dest_socket.connect((host, port))
                dest_socket.send(client_request)
                server_res = receive_until_close(dest_socket, buff_size)
                client_socket.send(server_res)
                dest_socket.close()
            #HTML para ser mostrado en el navegador
            #html = """<!DOCTYPE html>
            #        <html lang="es">
            #       <head>
            #            <meta charset="UTF-8">
            #            <title>CC4303</title>
            #        </head>
            #        <body>
            #            <h1>Bienvenide ... oh? no puedo ver tu nombre :c!</h1>
            #            <h3><a href="replace">¿Qué es un proxy?</a></h3>
            #        </body>
            #        </html> """
            #body_byte = html.encode()

            #Content length es el largo del html en bytes
            #content_length = len(body_byte)
            #Content type siempre es text/html
            #content_type = "text/html"

            #Armar estructura del response
            #responses = {
            #    "tipo": "Response",
            #    "start_line": {
            #        "version": "HTTP/1.1",
            #        "codigo": "200",
            #        "texto": "OK"
            #    },
            #    "headers": [
            #        f"Content-type: {content_type}",
            #        f"Content-length: {content_length}",
            #        "X-ElQuePregunta:" + name,
            #        "Connection: close"
            #    ],
            #    "body": body_byte
            #}

            #http_response = create_HTTP_message(responses)
            #print(http_response)
            #new_socket.send(http_response)
            #print("respuesta enviada")
            
            #print(f"tipo: {parsed_dict.get('tipo')}")
            #print(f"start line: {parsed_dict.get('start_line')}")
            #print(f"headers: {parsed_dict.get('headers')}")
            #print(f"body: {parsed_dict.get('body')}")

            #print("ejecutando create HTTP")
            #create_bytes = create_HTTP_message(parsed_dict)

            #print(create_bytes)

            #if recv_message == create_bytes:
                #print("Si")
            #else:
                #print("No")
        
        client_socket.close()
        print(f"conexion con {client_address} ha sido cerrada")