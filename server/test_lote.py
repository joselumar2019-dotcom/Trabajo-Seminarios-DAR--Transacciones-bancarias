import socket
import time

def test():
    s = socket.socket()
    s.connect(("127.0.0.1", 6345))
    def recv():
        data = s.recv(4096).decode()
        print("Server:", data)
        return data
        
    recv()
    print("Sending: cliente1")
    s.sendall(b"cliente1")
    time.sleep(0.1)
    recv()
    print("Sending: pass1234")
    s.sendall(b"pass1234") 
    time.sleep(0.1)
    recv()
    
    # Try valid lote
    lote = "1, 2 50, 3 20/n"
    print("Sending lote:", lote)
    s.sendall(lote.encode())
    time.sleep(0.1)
    ans = recv()
    if "confirmar?" in ans:
        s.sendall(b"si")
        time.sleep(0.1)
        recv()
        
test()
