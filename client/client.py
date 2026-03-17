import socket

host= "localhost"
port=6345
socket= socket.socket()
socket.connect((host,port))
print("Conectado a su banco virtual")
while True:
    input= raw_input()
    socket.send(input)

socket.close()

print("Hasta pronto")

