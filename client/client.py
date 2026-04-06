import socket

#host="192.168.1.134" esta es la IP si queremos conectarlo con MV
host= "localhost"
port=6345
cliente= socket.socket()
cliente.connect((host,port))
print("\nConectado a su banco virtual    :)\n")
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
    print("\nHasta pronto\nmáquina!")

