import socket
import time

def query(sock, cmd):
    print(f"Sending: {cmd}")
    sock.sendall((cmd + "\n").encode())
    time.sleep(0.5)
    try:
        data = sock.recv(65536).decode()
        print(f"Received ({len(data)} chars): {data[:200]}...")
        return data
    except Exception as e:
        print(f"Error reading: {e}")
        return ""

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2.0)
    s.connect(('localhost', 19542))
    print("Connected!")
    
    query(s, "*IDN?")
    query(s, ":VNA:TRAC:LIST?")
    query(s, ":VNA:TRACE:LIST?")
    query(s, ":VNA:TRAC:DATA? S11")
    query(s, ":VNA:TRACE:DATA? S11")
    
    s.close()
except Exception as e:
    print(f"Connection failed: {e}")
