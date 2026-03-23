import socket

host= "localhost"
port=6345
cliente= socket.socket()
cliente.connect((host,port))
print("Conectado a su banco virtual")
try:
    while True:
        # Recibir mensaje del servidor
        data = cliente.recv(4096)
        if not data:
            break
            
        mensaje = data.decode()
        print(mensaje, end="", flush=True)

        # Solo habilitamos la escritura si el servidor hace una pregunta
        if mensaje.endswith(": "):
            entrada = input()
            cliente.send(entrada.encode())
        else:
            print()

except KeyboardInterrupt:
    pass
finally:
    cliente.close()
    print("\nHasta pronto")

