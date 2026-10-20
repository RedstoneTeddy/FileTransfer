import socket 
import threading
import easygui # type: ignore
import struct
import json

def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # no packet is sent; this just selects a route
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"          # no network available
    finally:
        s.close()


def send_json(client_socket: socket.socket, data: dict) -> None:
    client_socket.sendall((json.dumps(data) + "\n").encode("utf-8"))


def receive_json(client_reader) -> dict:
    request_data = client_reader.readline()
    if not request_data:
        raise ConnectionError("Client disconnected")
    return json.loads(request_data.decode("utf-8"))


def receive_exact(client_reader, size: int) -> bytes:
    data = client_reader.read(size)
    if len(data) != size:
        raise ConnectionError(f"Expected {size} bytes, received {len(data)}")
    return data


def handle_client(data : dict[str, bytes], password : str, client_socket: socket.socket, client_address: tuple):
    print(f"Handling client {client_address}")
    client_reader = client_socket.makefile("rb")

    init_request = receive_json(client_reader)

    if init_request.get("password") != password:
        response_data : dict = {"status": "error", "message": "Invalid password"}
        send_json(client_socket, response_data)
        client_socket.close()
        print(f"Client {client_address} provided invalid password. Connection closed.")
        return

    print(f"Client {client_address} provided valid password.")
    response_data = {"status": "success", "message": "Password accepted"}
    send_json(client_socket, response_data)

    # Main Loop
    try:
        while True:
            # Get clients request
            request = receive_json(client_reader)

            match request.get("command"):
                case "push":
                    file_name : str = request.get("file_name") # type: ignore
                    print(f"Client {client_address} sent file: {file_name}")

                    size = struct.unpack("!I", receive_exact(client_reader, 4))[0]
                    file_data = receive_exact(client_reader, size)
                    print(f"File {file_name} of size {size} bytes received from client {client_address}.")
                    data[file_name] = file_data  # Store the file data in the dictionary

                case "pull":
                    file_name : str = request.get("file_name") # type: ignore
                    if file_name in data:
                        file_data = data[file_name]
                        size = len(file_data)
                        send_json(client_socket, {"status": "success", "size": size})
                        client_socket.sendall(file_data)
                        print(f"File {file_name} of size {size} bytes sent to client {client_address}.")
                    else:
                        response_data = {"status": "error", "message": f"File {file_name} not found on server"}
                        send_json(client_socket, response_data)
                        print(f"Client {client_address} requested non-existent file: {file_name}")
                    continue

                case "ls":
                    file_list = list(data.keys())
                    response_data = {"status": "success", "files": file_list}
                    send_json(client_socket, response_data)
                    continue

                case "exit":
                    print(f"Client {client_address} requested to exit.")
                    break

                case _:
                    raise ValueError(f"Unknown command: {request.get('command')}")

            # Send the client a response
            response_data = {"status": "success", "message": f"Command {request.get('command')} executed successfully"}
            send_json(client_socket, response_data)

    except Exception as e:
        print(f"An error occurred with client {client_address}: {e}")
    finally:
        client_reader.close()
        client_socket.close()
        print(f"Connection with client {client_address} closed.")








# Server setup
ip : str = get_local_ip()
data : dict[str, bytes] = {}
port : int = easygui.integerbox("Enter port number for the server:", "Port Input", lowerbound=4096, upperbound=65535) # type: ignore
password : str = easygui.passwordbox("Enter pin for the server:", "Password Input")
import key
key_code : str = key.encode(ip, port, int(password))
print(f"Server connection key: {key_code}")


server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((ip, port))
server_socket.listen(2)
print("Server started up and running...")
print(f"Server listening on {ip}:{port}")

while True:
    client_socket, client_address = server_socket.accept()
    print(f"Connection from {client_address} has been established.")
    client_thread = threading.Thread(target=handle_client, args=(data, password, client_socket, client_address))
    client_thread.start()

    