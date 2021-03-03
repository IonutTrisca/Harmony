# Harmony Voice App
This is a server - client type app used for voice and text chat. It is written in **python3** and it's using **kivy** as the framework for the GUI. The audio capture is handled by **pyaudio**.

## Requirements
Running `pip install -r requirements.txt` will install the necessary libraries. If that fails you can install **kivy** and **pyaudio** directly from pip.

## Using the app
First of all the server should be setup by running `python server.py`. The server requires the local IP address and a port number, and will ask you to enter them.

Regarding the client, `python main.py` will start up the client. In order to connect to the server you have to choose a nickname and enter the IP address and port of the server in the ip:port format.
If the server is behind a NAT, you will need to forward the port you have started the server on. In this case the clients will have to connect to the public IP address of the server, not the local one, but the server should still be setup with the local address.

## Interface

### Login Screen
![Login Screen](https://i.imgur.com/9fL1eZW.png)

### Main Interface
![Main Interface](https://i.imgur.com/5L1NWMr.png)

## Authors

* **Ionut Trisca**

## Contact

For any questions about this program you can contact me at **trisca46@gmail.com**.
