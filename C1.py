import socket 

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
    headers = header[1:]

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

    #Pasar body a bytes
    body_to_bytes = str(body).encode()

    #Construir headers
    header_lines = [start_line]

    #Unir head y pasar a bytes
    head_to_bytes = ("\r\n".join(header_lines) + "\r\n\r\n").encode()

    #Unir head y body
    return head_to_bytes + body_to_bytes
