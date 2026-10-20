import socket 
import easygui # type: ignore
import struct
import json
import os


def send_json(client_socket: socket.socket, data: dict) -> None:
    client_socket.sendall((json.dumps(data) + "\n").encode("utf-8"))


def receive_json(client_reader) -> dict:
    response_data = client_reader.readline()
    if not response_data:
        raise ConnectionError("Server disconnected")
    return json.loads(response_data.decode("utf-8"))


def receive_exact(client_reader, size: int) -> bytes:
    data = client_reader.read(size)
    if len(data) != size:
        raise ConnectionError(f"Expected {size} bytes, received {len(data)}")
    return data


server_ip : str = input("Enter server IP address: ")
server_port : int = int(input("Enter server port number: "))
server_password : str = input("Enter server pin: ")

try:
    client_socket : socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_ip, server_port))
    print(f"Connected to server at {server_ip}:{server_port}")
    server_reader = client_socket.makefile("rb")


    # Send the initial request
    init_request_data : dict = {"password": server_password}
    send_json(client_socket, init_request_data)

    # Receive the server's response
    response = receive_json(server_reader)
    if response.get("status") == "error":
        print(f"Server response: {response.get('message')}")
        client_socket.close()
        exit(1)

    # Main Loop
    while True:
        command : str = input("Enter command (push/pull/ls/exit): ")
        if command == "exit":
            print("Exiting client.")
            break

        if command == "push":
            file_path : str = easygui.fileopenbox("Select a file to push:", "File Selection") # type: ignore
            file_name : str = file_path.split("/")[-1] if file_path else ""
            if not file_path:
                print("No file selected. Please try again.")
                continue

            # Send the push command to the server
            request_data : dict = {"command": "push", "file_name": file_name}
            send_json(client_socket, request_data)

            # Send the file data to the server (this part is not implemented in the provided code)
            name = os.path.basename(file_path)
            size = os.path.getsize(file_path)
            client_socket.sendall(struct.pack('!I', size))  # Send the size of the file
            with open(file_path, 'rb') as f:
                while chunk := f.read(4096):
                    client_socket.sendall(chunk)  # Send the file in chunks
            print(f"File {name} of size {size} bytes sent to server.")
            

            # Receive the server's response
            response = receive_json(server_reader)
            if response.get("status") == "error":
                print(f"Server response: {response.get('message')}")
                continue
            if response.get("status") == "success":
                print(f"Server response: {response.get('message')}")
            else:
                print("Received unexpected response from server.")


        if command == "pull":
            file_name = input("Enter the name of the file to pull: ")
            if not file_name:
                print("No file name provided. Please try again.")
                continue

            # Send the pull command to the server
            request_data = {"command": "pull", "file_name": file_name}
            send_json(client_socket, request_data)

            response = receive_json(server_reader)
            if response.get("status") == "error":
                print(f"Server Error response: {response.get('message')}")
                continue
            size = response["size"]

            # Receive the file data from the server
            file_data = receive_exact(server_reader, size)

            # Save the received file data to a local file
            new_file_path = easygui.filesavebox("Save the received file as:", "Save File", default=file_name) # type: ignore
            if not new_file_path:
                print("No save location selected. File not saved.")
                continue
            with open(new_file_path, 'wb') as f: # type: ignore
                f.write(file_data)
            print(f"File {file_name} of size {size} bytes received from server and saved locally.")

        if command == "ls":
            # Send the ls command to the server
            request_data = {"command": "ls"}
            send_json(client_socket, request_data)

            # Receive the server's response
            response = receive_json(server_reader)
            if response.get("status") == "error":
                print(f"Server response: {response.get('message')}")
                continue
            if response.get("status") == "success":
                file_list = response.get("files", [])
                print("Files on server:")
                for file in file_list:
                    print(f"- {file}")
            else:
                print("Received unexpected response from server.")



        if command == "exit":
            print("Exiting client.")
            request_data = {"command": "exit"} 
            send_json(client_socket, request_data)
            client_socket.close()
            break
            




except Exception as e:
    print(f"Failed to connect to server at {server_ip}:{server_port}. Error: {e}")
    exit(1)