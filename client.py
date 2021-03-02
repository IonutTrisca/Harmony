import socket
import threading
import time
import pyaudio
import json
from utils import *

ID_LENGTH = 8

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 12000
CHUNK = 512

ENCODING = 'ascii'
MESSAGELEN = 5

NO_MESSAGE = "null"

class Client:
    def __init__(self, server_ip, server_port) -> None:
        self.connected = False
        self.server = (server_ip, server_port)

        self.audio_streams = dict()
        self.input_stream = pyaudio.PyAudio().open(format=FORMAT,
                                                    channels=CHANNELS,
                                                    rate=RATE,
                                                    input=True,
                                                    frames_per_buffer=CHUNK)
        
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.nickname = ""
        self.received_msg = ""
        self.shutdown = False
        self.voice_connected = False
        self.muted = False
        self.connected_clients = []

    def recv_data(self):
        remaining_data = MESSAGELEN
        data = bytes()

        while remaining_data != 0:
            tmp_data = self.tcp_socket.recv(remaining_data)
            data += tmp_data
            remaining_data -= len(tmp_data)

        length = int(data.decode(ENCODING))

        remaining_data = length
        data = bytes()

        while remaining_data != 0:
            tmp_data = self.tcp_socket.recv(remaining_data)
            data += tmp_data
            remaining_data -= len(tmp_data)

        return data.decode(ENCODING)

    def send_data(self, data):
        length = get_number_bytes_str(data)
        self.tcp_socket.sendall(length.encode(ENCODING))
        self.tcp_socket.sendall(data.encode(ENCODING))

    def server_handshake(self):
        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.connect(self.server)

        self.id = self.recv_data()

        print(f"Received id {self.id}")
        self.send_data(self.nickname)
        
        self.connected = True
        
        remote_clients = json.loads(self.recv_data())

        for client in remote_clients:
            rem_client = RemoteClient()
            rem_client.id = client['id']
            rem_client.nickname = client['nick']
            rem_client.voice_connected = client['voice']
            
            self.connected_clients.append(rem_client)


        self.udp_socket.sendto((self.id + "HELLOUDP").encode(ENCODING), self.server)


    def transmit_voice(self):
        while not self.shutdown:
            if self.voice_connected and not self.muted:
                data = self.input_stream.read(CHUNK)
                message = bytearray(self.id.encode(ENCODING))
                message.extend(data)

                try:
                    self.udp_socket.sendto(bytes(message), self.server)
                except socket.error:
                    print("Socket Error")
                    break
            else:
                time.sleep(0.2)


    def receive_voices(self):
        while not self.shutdown:
            try:
                message, _ = self.udp_socket.recvfrom(CHUNK * 2 + ID_LENGTH)
            except socket.error:
                print("UDP Socket Error")
                break

            client_id = message[0:ID_LENGTH]
            data = message[ID_LENGTH:CHUNK * 2 + ID_LENGTH]
            
            client_id = client_id.decode(ENCODING)

            if client_id in self.audio_streams:
                self.audio_streams[client_id].write(data)
                
            else:
                audio_stream = pyaudio.PyAudio()
                self.audio_streams[client_id] = audio_stream.open(format=FORMAT,
                                            channels=CHANNELS,
                                            rate=RATE,
                                            output=True,
                                            frames_per_buffer=CHUNK)
                self.audio_streams[client_id].write(data)

    def send_message(self, message):
        message = f"{self.nickname}: " + message
        self.send_data(to_json(message, "MSG"))

    def start(self):
        self.send_voice_thread = threading.Thread(target=self.transmit_voice)
        self.send_voice_thread.start()

        self.recv_voice_thread = threading.Thread(target=self.receive_voices)
        self.recv_voice_thread.start()
    
    def join_threads(self):
        self.send_voice_thread.join()
        self.recv_voice_thread.join()
        print("Threads joined")