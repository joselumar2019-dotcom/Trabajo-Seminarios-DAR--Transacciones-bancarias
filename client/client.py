import socket

host= "localhost"
port=6345
socket= socket.socket()
socket.connect((host,port))
print("Conectado a su banco virtual")
while True:
    # Recibir mensaje del servidor
    data = socket.recv(1024)   # hasta 1024 bytes
    if data:
        print("Servidor:", data.decode())

    # Enviar mensaje al servidor
    entrada = input()
    socket.send(entrada.encode())
socket.close()

print("Hasta pronto")

