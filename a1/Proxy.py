# Include the libraries for socket and system calls
import socket
import sys
import os
import argparse
import re
import time
from datetime import datetime, timedelta

# 1MB buffer size
BUFFER_SIZE = 1000000

# Get the IP address and Port number to use for this web proxy server
parser = argparse.ArgumentParser()
parser.add_argument('hostname', help='the IP Address Of Proxy Server')
parser.add_argument('port', help='the port number of the proxy server')
args = parser.parse_args()
proxyHost = args.hostname
proxyPort = int(args.port)

# Create a server socket, bind it to a port and start listening
try:
  # Create a server socket
  # ~~~~ INSERT CODE ~~~~
  serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  # ~~~~ END CODE INSERT ~~~~
  print ('Created socket')
except:
  print ('Failed to create socket')
  sys.exit()

try:
  # Bind the the server socket to a host and port
  # ~~~~ INSERT CODE ~~~~
  serverSocket.bind((proxyHost, proxyPort))
  # ~~~~ END CODE INSERT ~~~~
  print ('Port is bound')
except:
  print('Port is already in use')
  sys.exit()

try:
  # Listen on the server socket
  # ~~~~ INSERT CODE ~~~~
  serverSocket.listen(10)  # Increased backlog for better performance
  # ~~~~ END CODE INSERT ~~~~
  print ('Listening to socket')
except:
  print ('Failed to listen')
  sys.exit()

# Helper function to check if cache is fresh
def is_cache_fresh(cache_headers, client_headers):
  # Extract cache control headers
  cache_date = None
  cache_last_modified = None
  cache_etag = None
  
  for line in cache_headers:
    if line.lower().startswith('date:'):
      cache_date = line.split(':', 1)[1].strip()
    elif line.lower().startswith('last-modified:'):
      cache_last_modified = line.split(':', 1)[1].strip()
    elif line.lower().startswith('etag:'):
      cache_etag = line.split(':', 1)[1].strip()
  
  # Extract client conditional headers
  if_modified_since = None
  if_none_match = None
  
  for line in client_headers:
    if line.lower().startswith('if-modified-since:'):
      if_modified_since = line.split(':', 1)[1].strip()
    elif line.lower().startswith('if-none-match:'):
      if_none_match = line.split(':', 1)[1].strip()
  
  # Check if client has conditional headers that match cache
  if if_modified_since and cache_last_modified:
    if if_modified_since == cache_last_modified:
      return False
  
  if if_none_match and cache_etag:
    if if_none_match == cache_etag:
      return False
  
  # Check if cache is older than 5 minutes
  if cache_date:
    try:
      # Basic check if cache is too old (5 minutes)
      cache_time = time.strptime(cache_date, "%a, %d %b %Y %H:%M:%S GMT")
      cache_time = time.mktime(cache_time)
      current_time = time.time()
      if current_time - cache_time > 300:  # 5 minutes in seconds
        return False
    except:
      return False
  
  return True

# continuously accept connections
while True:
  print ('Waiting for connection...')
  clientSocket = None

  # Accept connection from client and store in the clientSocket
  try:
    # ~~~~ INSERT CODE ~~~~
    clientSocket, clientAddress = serverSocket.accept()
    # ~~~~ END CODE INSERT ~~~~
    print ('Received a connection')
  except:
    print ('Failed to accept connection')
    sys.exit()

  # Get HTTP request from client
  # and store it in the variable: message_bytes
  # ~~~~ INSERT CODE ~~~~
  message_bytes = clientSocket.recv(BUFFER_SIZE)
  # ~~~~ END CODE INSERT ~~~~
  message = message_bytes.decode('utf-8')
  print ('Received request:')
  print ('< ' + message)

  # Extract the method, URI and version of the HTTP client request 
  requestParts = message.split()
  if len(requestParts) < 3:
    clientSocket.close()
    continue
    
  method = requestParts[0]
  URI = requestParts[1]
  version = requestParts[2]

  print ('Method:\t\t' + method)
  print ('URI:\t\t' + URI)
  print ('Version:\t' + version)
  print ('')

  # Get the requested resource from URI
  # Remove http protocol from the URI
  URI = re.sub('^(/?)http(s?)://', '', URI, count=1)

  # Remove parent directory changes - security
  URI = URI.replace('/..', '')

  # Split hostname from resource name
  resourceParts = URI.split('/', 1)
  hostname = resourceParts[0]
  resource = '/'

  if len(resourceParts) == 2:
    # Resource is absolute URI with hostname and resource
    resource = resource + resourceParts[1]

  print ('Requested Resource:\t' + resource)
  
  # Parse client headers for conditional requests
  client_headers = message.split('\r\n')
  use_cached = False
  
  # Check if resource is in cache
  try:
    cacheLocation = './' + hostname + resource
    if cacheLocation.endswith('/'):
        cacheLocation = cacheLocation + 'default'

    print ('Cache location:\t\t' + cacheLocation)

    fileExists = os.path.isfile(cacheLocation)
    
    if not fileExists:
      raise FileNotFoundError("Cache miss")
    
    # Check whether the file is currently in the cache
    cacheFile = open(cacheLocation, "r")
    cacheData = cacheFile.readlines()
    
    # Check if cache is fresh
    if is_cache_fresh(cacheData, client_headers):
      print ('Cache hit! Loading from cache file: ' + cacheLocation)
      # ProxyServer finds a cache hit
      # Send back response to client 
      # ~~~~ INSERT CODE ~~~~
      # Update the Date header to current time
      response_with_updated_headers = []
      date_updated = False
      
      for line in cacheData:
        if line.lower().startswith('date:'):
          # Update the Date header to current time
          current_time = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
          response_with_updated_headers.append(f'Date: {current_time}\r\n')
          date_updated = True
        else:
          response_with_updated_headers.append(line)
      
      # Add Date header if not present
      if not date_updated:
        current_time = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        response_with_updated_headers.insert(1, f'Date: {current_time}\r\n')
      
      clientSocket.sendall(''.join(response_with_updated_headers).encode())
      # ~~~~ END CODE INSERT ~~~~
      cacheFile.close()
      print ('Sent to the client:')
      print ('> ' + ''.join(response_with_updated_headers))
      use_cached = True
    else:
      raise FileNotFoundError("Cache expired")
  except:
    use_cached = False
    
  if not use_cached:
    # cache miss or expired. Get resource from origin server
    originServerSocket = None
    # Create a socket to connect to origin server
    # and store in originServerSocket
    # ~~~~ INSERT CODE ~~~~
    originServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # ~~~~ END CODE INSERT ~~~~

    print ('Connecting to:\t\t' + hostname + '\n')
    try:
      # Get the IP address for a hostname
      address = socket.gethostbyname(hostname)
      # Connect to the origin server
      # ~~~~ INSERT CODE ~~~~
      originServerSocket.connect((address, 80))
      # ~~~~ END CODE INSERT ~~~~
      print ('Connected to origin Server')

      originServerRequest = ''
      originServerRequestHeader = ''
      # Create origin server request line and headers to send
      # and store in originServerRequestHeader and originServerRequest
      # originServerRequest is the first line in the request and
      # originServerRequestHeader is the second line in the request
      # ~~~~ INSERT CODE ~~~~
      originServerRequest = method + " " + resource + " " + version
      originServerRequestHeader = "Host: " + hostname
      
      # Forward relevant headers from client request
      headers = message.split('\r\n')
      for header in headers[1:]:  # Skip the request line
        if header == '':
          break
        
        header_name = header.split(':', 1)[0].lower()
        # Forward important headers
        if header_name in ['if-modified-since', 'if-none-match', 'user-agent', 'accept', 'cookie']:
          originServerRequestHeader += "\r\n" + header
      
      # Add Connection: keep-alive to request
      originServerRequestHeader += "\r\nConnection: keep-alive"
      # ~~~~ END CODE INSERT ~~~~

      # Construct the request to send to the origin server
      request = originServerRequest + '\r\n' + originServerRequestHeader + '\r\n\r\n'

      # Request the web resource from origin server
      print ('Forwarding request to origin server:')
      for line in request.split('\r\n'):
        print ('> ' + line)

      try:
        originServerSocket.sendall(request.encode())
      except socket.error:
        print ('Forward request to origin failed')
        sys.exit()

      print('Request sent to origin server\n')

      # Get the response from the origin server
      # ~~~~ INSERT CODE ~~~~
      responseData = b''
      originServerSocket.settimeout(5.0)  # Set timeout to avoid hanging
      
      try:
        while True:
          part = originServerSocket.recv(BUFFER_SIZE)
          if not part:
            break
          responseData += part
          
          # Check if we've received the full response
          if b'\r\n\r\n' in responseData:
            # Check if this is a chunked response
            headers = responseData.split(b'\r\n\r\n', 1)[0]
            if b'Transfer-Encoding: chunked' in headers:
              # Continue receiving for chunked encoding
              continue
            
            # For non-chunked responses, check Content-Length
            if b'Content-Length:' in headers:
              # Extract content length
              content_length_header = re.search(b'Content-Length: *([0-9]+)', headers)
              if content_length_header:
                content_length = int(content_length_header.group(1))
                if len(responseData.split(b'\r\n\r\n', 1)[1]) >= content_length:
                  break
            else:
              # If no content length and not chunked, we've received everything
              break
              
      except socket.timeout:
        # Timeout occurred, but we may have partial data
        pass
      # ~~~~ END CODE INSERT ~~~~

      # Send the response to the client
      # ~~~~ INSERT CODE ~~~~
      # Check if we need to update any headers
      if responseData:
        response_text = responseData.decode('utf-8', errors='replace')
        header_part, body_part = response_text.split('\r\n\r\n', 1) if '\r\n\r\n' in response_text else (response_text, '')
        headers = header_part.split('\r\n')
        
        # Update the Date header
        updated_headers = []
        date_updated = False
        connection_updated = False
        
        for header in headers:
          if header.lower().startswith('date:'):
            current_time = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
            updated_headers.append(f'Date: {current_time}')
            date_updated = True
          elif header.lower().startswith('connection:'):
            # Preserve keep-alive if possible
            if 'keep-alive' in header.lower():
              updated_headers.append(header)
            else:
              updated_headers.append('Connection: keep-alive')
            connection_updated = True
          else:
            updated_headers.append(header)
        
        # Add Date header if not present
        if not date_updated:
          current_time = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
          updated_headers.insert(1, f'Date: {current_time}')
        
        # Add Connection header if not present
        if not connection_updated:
          updated_headers.append('Connection: keep-alive')
        
        # Reconstruct the response
        updated_response = '\r\n'.join(updated_headers) + '\r\n\r\n' + body_part
        clientSocket.sendall(updated_response.encode())
      else:
        clientSocket.sendall(responseData)
      # ~~~~ END CODE INSERT ~~~~

      # Create a new file in the cache for the requested file.
      cacheDir, file = os.path.split(cacheLocation)
      print ('cached directory ' + cacheDir)
      if not os.path.exists(cacheDir):
        os.makedirs(cacheDir)
      cacheFile = open(cacheLocation, 'wb')

      # Save origin server response in the cache file
      # ~~~~ INSERT CODE ~~~~
      # For caching, store the original response with our date update
      if responseData:
        response_text = responseData.decode('utf-8', errors='replace')
        header_part, body_part = response_text.split('\r\n\r\n', 1) if '\r\n\r\n' in response_text else (response_text, '')
        headers = header_part.split('\r\n')
        
        # Update the Date header for cache
        updated_headers = []
        date_updated = False
        
        for header in headers:
          if header.lower().startswith('date:'):
            current_time = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
            updated_headers.append(f'Date: {current_time}')
            date_updated = True
          else:
            updated_headers.append(header)
        
        # Add Date header if not present
        if not date_updated:
          current_time = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
          updated_headers.insert(1, f'Date: {current_time}')
        
        # Reconstruct the response for caching
        updated_response = '\r\n'.join(updated_headers) + '\r\n\r\n' + body_part
        cacheFile.write(updated_response.encode())
      else:
        cacheFile.write(responseData)
      # ~~~~ END CODE INSERT ~~~~
      cacheFile.close()
      print ('cache file closed')

      # finished communicating with origin server - shutdown socket writes
      print ('origin response received. Closing sockets')
      originServerSocket.close()
      
      # Don't shutdown write end of client socket to allow keep-alive
      # clientSocket.shutdown(socket.SHUT_WR)
      print ('Origin server connection closed')
    except OSError as err:
      print ('origin server request failed. ' + str(err))

  # Check if we should keep the connection alive
  if 'Connection: keep-alive' in message:
    # Set a timeout for the next request
    clientSocket.settimeout(5.0)
    try:
      # Try to receive another request
      next_request = clientSocket.recv(BUFFER_SIZE, socket.MSG_PEEK)
      if not next_request:
        clientSocket.close()
        print('Client closed connection')
    except socket.timeout:
      clientSocket.close()
      print('Connection timeout, closing socket')
    except:
      clientSocket.close()
      print('Failed to receive next request, closing socket')
  else:
    try:
      clientSocket.close()
      print('Connection: close header found, closing socket')
    except:
      print('Failed to close client socket')
