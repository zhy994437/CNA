import socket
import sys
import os
import argparse
import re
import datetime
from urllib.parse import urlparse

BUFFER_SIZE = 1000000

def parse_headers(response):
    headers = {}
    lines = response.split('\r\n')
    for line in lines:
        parts = line.split(': ', 1)
        if len(parts) == 2:
            headers[parts[0]] = parts[1]
    return headers

def is_cache_valid(headers):
    if "Expires" in headers:
        try:
            expires = datetime.datetime.strptime(headers["Expires"], "%a, %d %b %Y %H:%M:%S GMT")
            return expires > datetime.datetime.utcnow()
        except ValueError:
            return False
    return False

# Create and bind proxy server socket
parser = argparse.ArgumentParser()
parser.add_argument('hostname', help='IP Address Of Proxy Server')
parser.add_argument('port', help='Port Number of Proxy Server')
args = parser.parse_args()
proxyHost = args.hostname
proxyPort = int(args.port)

serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serverSocket.bind((proxyHost, proxyPort))
serverSocket.listen(5)

while True:
    clientSocket, clientAddress = serverSocket.accept()
    message_bytes = clientSocket.recv(BUFFER_SIZE)
    message = message_bytes.decode('utf-8')

    requestParts = message.split()
    method, URI, version = requestParts[0], requestParts[1], requestParts[2]
    parsed_url = urlparse(URI)
    hostname, port = parsed_url.hostname, parsed_url.port or 80
    resource = parsed_url.path or "/"
    cacheLocation = f'./cache/{hostname}{resource.replace("/", "_")}'

    # Check cache validity
    if os.path.isfile(cacheLocation):
        with open(cacheLocation, 'r') as cacheFile:
            cacheData = cacheFile.read()
            headers = parse_headers(cacheData)
            if is_cache_valid(headers):
                clientSocket.sendall(cacheData.encode())
                clientSocket.close()
                continue
    
    # Connect to origin server
    originServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    originServerSocket.connect((hostname, port))
    request = f"{method} {resource} {version}\r\nHost: {hostname}\r\nConnection: close\r\n\r\n"
    originServerSocket.sendall(request.encode())
    
    # Receive response
    responseData = b''
    while True:
        part = originServerSocket.recv(BUFFER_SIZE)
        if not part:
            break
        responseData += part
    
    # Save response to cache
    os.makedirs(os.path.dirname(cacheLocation), exist_ok=True)
    with open(cacheLocation, 'wb') as cacheFile:
        cacheFile.write(responseData)
    
    # Send response to client
    clientSocket.sendall(responseData)
    clientSocket.close()
    originServerSocket.close()
    
    # Pre-fetch resources from HTML
    if b'text/html' in responseData:
        html = responseData.decode(errors='ignore')
        urls = re.findall(r'(?:href|src)=["\'](.*?)["\']', html)
        for url in urls:
            if url.startswith("http"):
                urlparse(url).path  # Implement pre-fetch logic
