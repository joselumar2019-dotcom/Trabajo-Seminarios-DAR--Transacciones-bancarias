import socket
serv=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serv.bind(("", 6345))
serv.listen(1)
cli, addr = serv.accept()
while True:
    recibir= cli.recv(1024)
    print("Recibo conexion de la IP: " + str(addr[0]) + " Puerto: " + str(addr[1]))
    cli.send()


cli.close()
serv.close()

print("Cierre de conexión")



