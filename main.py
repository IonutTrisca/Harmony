import time
import socket
import json

from threading import Thread

from utils import *

from kivy.app import App
from kivy.lang import Builder
from kivy.config import Config
from kivy.uix.popup import Popup
from kivy.properties import ObjectProperty
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import Screen, ScreenManager

from client import Client

Window.clearcolor = (0.2, 0.2, 0.2, 1)
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

CMD = "CMD"
MSG = "MSG"
NO_MESSAGE = "null"

message_recv_thread = None
cli = None

class VoiceConnectedClient(FloatLayout):
    client_name = ObjectProperty(None)
    client_image = ObjectProperty(None)
    pass

class ConnectedClient(FloatLayout):
    client_name = ObjectProperty(None)
    client_image = ObjectProperty(None)
    pass


class NeedNicknameException(Exception):
    pass

class PopUpWindow(FloatLayout):
    window_text = ObjectProperty(None)
    pass

class LoginWindow(Screen):
    ip = ObjectProperty(None)
    nick = ObjectProperty(None)
    
    def on_pre_enter(self):
        Window.size = (1280, 720)

    def connect(self):
        if message_recv_thread is not None:
            message_recv_thread.join()

        global cli

        ip_port = self.ip.text.split(":")

        try:
            ip = socket.gethostbyname(ip_port[0])
            port = 26030

            if len(ip_port) == 2:
                port = int(ip_port[1])

            self.ip.text = ""

            cli = Client(ip, port)

            if self.nick.text == "":
                raise NeedNicknameException()
            cli.nickname = self.nick.text
            

            cli.server_handshake()
            cli.start()

            if cli.connected:
                wm.current = "main"

        except NeedNicknameException:
            self.no_nickname()
        except socket.error:
            self.wrong_server_data()
            self.ip.text = ""
    
    def wrong_server_data(self):
        show = PopUpWindow()
        show.window_text.text = "Wrong port, IP \n or server is not available."
        popupWindow = Popup(title="Wrong info", content=show, size_hint=(0.3,0.3))
        popupWindow.open()

    def no_nickname(self):
        show = PopUpWindow()
        show.window_text.text = "You need to enter a nickname"
        popupWindow = Popup(title="No nickname provided", content=show, size_hint=(0.3,0.3))
        popupWindow.open()
        

class MainWindow(Screen):
    recv_messages = ObjectProperty(None)
    send_mesg = ObjectProperty(None)
    online_voice_clients_widgets = ObjectProperty(None)
    online_clients_widgets = ObjectProperty(None)
    connect_voice = ObjectProperty(None)
    mute_client = ObjectProperty(None)
    user_name = ObjectProperty(None)

    voice_connected_clients = []
    connected_clients = []

    def send_message(self):
        if self.send_mesg.text != "":
            cli.send_message(self.send_mesg.text)
        self.send_mesg.text = ""

    def on_pre_enter(self):
        for client in cli.connected_clients:
            vcc = VoiceConnectedClient()
            cc = ConnectedClient()
            vcc.client_name.text = client.nickname
            cc.client_name.text = client.nickname

            if client.voice_connected:
                self.voice_connected_clients.append((vcc, client.id))
                self.online_voice_clients_widgets.add_widget(vcc)

            self.connected_clients.append((cc, client.id))
            self.online_clients_widgets.add_widget(cc)
            
        self.user_name.text = cli.nickname

        global message_recv_thread
        message_recv_thread = Thread(target=self.recv_msg)
        message_recv_thread.start()

    def connect_voice_channel(self):
        cli.voice_connected = not cli.voice_connected
        if cli.voice_connected:
            self.connect_voice.text = "Disconnect Voice"
            cli.send_data(to_json(NO_MESSAGE, "VOICE_CONN"))

        else:
            self.connect_voice.text = "Connect Voice"
            cli.send_data(to_json(NO_MESSAGE, "VOICE_DISC"))

    def mute(self):
        cli.muted = not cli.muted
        if cli.muted:
            self.mute_client.text = "Unmute"
        else:
            self.mute_client.text = "Mute"

    def recv_msg(self):
        global cli
        while not cli.shutdown:
            try:
                recv_message = json.loads(cli.recv_data())
            except socket.error:
                print("Error while receiving data")
                cli.shutdown = True
                
                if App.get_running_app() is not None:
                    show = PopUpWindow()
                    show.window_text.text = "There has been an error\n while receiving a message\n\n Please reconnect"
                    popupWindow = Popup(title="Server Communication Error", content=show, size_hint=(0.3,0.3))
                    popupWindow.open()
                    time.sleep(2)
                    break

            if recv_message['type'] == MSG:
                cli.received_msg += recv_message['body'] + "\n"
                self.recv_messages.text = cli.received_msg
                continue

            if recv_message['type'] == "USER_VOICE_CONN":
                for client in cli.connected_clients:
                    if client.id == recv_message['body']:
                        client.voice_connected = True
                        text = VoiceConnectedClient()
                        text.client_name.text = client.nickname
                        self.voice_connected_clients.append((text, client.id))
                        self.online_voice_clients_widgets.add_widget(text)
                
            if recv_message['type'] == "USER_VOICE_DISC":
                rm_client = None
                for (text, client_id) in self.voice_connected_clients:
                    if client_id == recv_message['body']:
                        self.online_voice_clients_widgets.remove_widget(text)
                        for client in cli.connected_clients:
                            if client.id == recv_message['body']:
                                client.voice_connected = False
                        rm_client = (text, client_id)
                        break
                
                try:
                    self.voice_connected_clients.remove(rm_client)
                except:
                    print("Client not voice connected")

            if recv_message['type'] == "USER_CONN":
                client_attr = recv_message['body']
                client = RemoteClient()
                client.id = client_attr['id']
                client.nickname = client_attr['nick']
                client.voice_connected = client_attr['voice']

                cli.connected_clients.append(client)

                text = ConnectedClient()
                text.client_name.text = client.nickname
                self.connected_clients.append((text, client.id))
                self.online_clients_widgets.add_widget(text)
                
            if recv_message['type'] == "USER_DISC":
                rm_client = None
                for (text, client_id) in self.connected_clients:
                    if client_id == recv_message['body']:
                        self.online_clients_widgets.remove_widget(text)
                        rm_client = (text, client_id)
                
                try:
                    self.connected_clients.remove(rm_client)
                except:
                    print("Client not connected")
        
        wm.current = "login"
        wm.remove_widget(screens[1])
        wm.add_widget(MainWindow(name="main"))
        cli.tcp_socket.close()
        cli.udp_socket.close()
        cli.join_threads()


class WindowManager(ScreenManager):
    pass


kv = Builder.load_file('harmony.kv')
wm = WindowManager()

screens = [LoginWindow(name="login"),MainWindow(name="main")]
for screen in screens:
    wm.add_widget(screen)

wm.current = "login"

class HarmonyVoiceApp(App):
    def build(self):
        return wm

if __name__ == '__main__':
    HarmonyVoiceApp().run()
    
    if cli is not None:
        cli.shutdown = True
        try:
            cli.send_data(to_json(NO_MESSAGE, "SD"))
        except:
            print("No connection to the server")
        
        if cli.connected:
            cli.tcp_socket.close()
            cli.udp_socket.close()
            cli.join_threads()
        
        if message_recv_thread is not None:
            message_recv_thread.join()
    
