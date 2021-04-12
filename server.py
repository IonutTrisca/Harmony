import socket
import random
import string
import threading
import json
import time
from utils import *

ID_LENGTH = 8
CHUNK = 512

ENCODING = 'ascii'
MESSAGELEN = 5

NO_MESSAGE = "null"

class ServerSideClient:
    def __init__(self) -> None:
        self.connection = ""
        self.id = ""
        self.udp_address = ""
        self.nickname = ""
        self.voice_connected = False


class Server:
    def __init__(self, server_ip, server_port) -> None:
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.bind((server_ip, server_port))
        self.tcp_socket.listen()
        self.clients = []

        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.bind((server_ip, server_port))

    def get_new_id(self) -> string:
        letters = string.ascii_lowercase
        result_str = ''.join(random.choice(letters) for i in range(ID_LENGTH))
        return result_str
    
    def recv_data(self, socket):
        remaining_data = MESSAGELEN
        data = bytes()

        while remaining_data != 0:
            tmp_data = socket.recv(remaining_data)
            data += tmp_data
            remaining_data -= len(tmp_data)

        length = int(data.decode(ENCODING))

        remaining_data = length
        data = bytes()

        while remaining_data != 0:
            tmp_data = socket.recv(remaining_data)
            data += tmp_data
            remaining_data -= len(tmp_data)

        return data.decode(ENCODING)

    def send_data(self, data, socket):
        length = get_number_bytes_str(data)
        socket.sendall(length.encode(ENCODING))
        socket.sendall(data.encode(ENCODING))

    def accept_new_connections(self):
        while True:
            # accept new connection
            try:
                client, address = self.tcp_socket.accept()
            except:
                print("TCP socket closed")
                break

            print(f"Connected with {str(address)}")

            # create a new client
            new_client = ServerSideClient()
            new_client.connection = client

            # generate and send its id and receive it back
            new_client.id = self.get_new_id()
            print(f"Client received ID {new_client.id}")

            self.send_data(new_client.id, new_client.connection)

            new_client.nickname = self.recv_data(new_client.connection)
            
            clients = []

            for client in self.clients:
                client_str = dict()
                client_str['id'] = client.id
                client_str['nick'] = client.nickname
                client_str['voice'] = client.voice_connected
                clients.append(client_str)
            
            json_data = json.dumps(clients)
            self.send_data(json_data, new_client.connection)
            
            self.clients.append(new_client)

            client_str = dict()
            client_str['id'] = new_client.id
            client_str['nick'] = new_client.nickname
            client_str['voice'] = new_client.voice_connected

            self.tcp_broadcast(to_json(client_str, "USER_CONN"))

            thread = threading.Thread(target=self.handle_client, args=(new_client,))
            thread.start()

    
    def tcp_conn_check(self, client):
        self.send_data(to_json(NO_MESSAGE, "KEEP_ALIVE"), client.connection)
        time.sleep(0.5)

    def handle_client(self, client):
        print("Client is active")
        while True:
            try:
                message = json.loads(self.recv_data(client.connection))
                
                if message['type'] == "VOICE_CONN":
                    client.voice_connected = True
                    self.tcp_broadcast(to_json(client.id, "USER_VOICE_CONN"))
                    continue

                if message['type'] == "VOICE_DISC":
                    client.voice_connected = False
                    self.tcp_broadcast(to_json(client.id, "USER_VOICE_DISC"))
                    continue
                
                if message['type'] == "MSG":
                    self.tcp_broadcast(json.dumps(message))

            except socket.error:
                self.clients.remove(client)
                client.connection.close()
                self.tcp_broadcast(to_json(client.id, "USER_VOICE_DISC"))
                self.tcp_broadcast(to_json(client.id, "USER_DISC"))
                print(f'{client.nickname} left due to socket closure!')
                break

    def has_client_connected(self, client_id, address) -> bool:
        for i in range(0, len(self.clients)):
            if self.clients[i].id == client_id:
                return True

        return False
    
    def handle_voice_data(self):
        while True:
            try:
                message, address = self.udp_socket.recvfrom(CHUNK * 2 + ID_LENGTH)
                client_id = message[0:ID_LENGTH].decode(ENCODING)

                if len(message) != 16:
                    if self.has_client_connected(client_id, address):
                        self.udp_broadcast(message, address)
                else:
                    for i in range(0, len(self.clients)):
                        if self.clients[i].id == client_id:
                            if self.clients[i].udp_address == "":
                                self.clients[i].udp_address = address
            except socket.error:
                print("UDP socket closed")
                break

    def tcp_broadcast(self, message):
        for client in self.clients:
            self.send_data(message, client.connection)
    

    def udp_broadcast(self, message, address):
        for client in self.clients:
            if client.voice_connected:
                if address != client.udp_address and client.udp_address != "":
                    self.udp_socket.sendto(bytes(message), client.udp_address)

    def get_commands(self):
        command = input("")
        if command == "exit":
            for client in self.clients:
                client.connection.close()

            self.tcp_socket.close()
            self.udp_socket.close()
            
            exit()

    def start(self):
        tcp_conn_thread = threading.Thread(target=self.accept_new_connections, daemon=True)
        tcp_conn_thread.start()
        print("TCP Thread Active.")

        udp_voice_thread = threading.Thread(target=self.handle_voice_data, daemon=True)
        udp_voice_thread.start()
        print("UDP Thread Active.")

        command_thread = threading.Thread(target=self.get_commands)
        command_thread.start()




if __name__ == "__main__":
    print("If the server is behind a NAT you will have to use port forwarding for internet connections.\n")

    IP = input("Please enter the local IP of the host: ")
    PORT = int(input("Please enter a port for the server: "))
    # IP = '192.168.0.20'
    # PORT = 26030
    server = Server(IP, PORT)
    print("Server is listening for connections...")
    server.start()
