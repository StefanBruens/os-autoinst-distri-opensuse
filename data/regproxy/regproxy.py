import socket
import socketserver
import ssl
import sys
import re
import http.client
import json
import _thread

def availableRepos(prefix):
	conn = http.client.HTTPSConnection("obs-login.opensuse.org")
	headers={"Host": "registry.opensuse.org"}
	conn.request("GET", "/v2/_catalog", None, headers)
	resp = conn.getresponse()
	data = json.loads(resp.read())
	all_repos = data["repositories"]
	return [repo[len(prefix):] for repo in all_repos if repo.startswith(prefix)]

prefix = sys.argv[1]
if prefix[-1] != '/':
	prefix += '/' # Make sure prefix ends with /

proxied_repos = availableRepos(prefix)
print("Proxying repos: %s\n" % (", ".join(proxied_repos)))
sys.stdout.flush()

class RegProxy(socketserver.StreamRequestHandler):
	"""A proxy which rewrites /v2/ Docker Registry API requests to prepend
	   a given prefix to the namespace, if the repo exists in the prefix."""
	def rewritePath(self, path):
		"""Try to HEAD path with prefix prepended to the namespace
		on the real registry and if it works, return the rewritten path."""
		if path[:4] != "/v2/":
			return path

		proxy = False
		for repo in proxied_repos:
			if path[4:5+len(repo)] == repo + "/":
				proxy = True
				break

		newpath = "/v2/" + prefix + path[4:]
		return newpath if proxy else path

	def relayHttp(self, sock, requestline):
		# Send request line
		sock.write(requestline)

		# No keepalive
		sock.write(b"Connection: close\r\n")

		# Send all headers from client to server
		while True:
			line = self.rfile.readline(65537)
			sock.write(line)
			if line == b"\r\n":
				break

		# Send the reply from server to client
		while True:
			buf = sock.read(1024)
			if not buf:
				break
			self.wfile.write(buf)

	def handle(self):
		# Read and disassmeble the request line
		requestline = self.rfile.readline(65537)
		(method, query, version) = requestline.decode("utf-8").split(" ")
		# Rewrite the path
		newquery = self.rewritePath(query)
		print("Request to %s rewritten to %s\n" % (query, newquery))
		sys.stdout.flush()
		# Reassemble the request line
		requestline = " ".join([method, newquery, version]).encode("utf-8");

		# Create a connection to the real registry
		context = ssl.create_default_context()
		# registry.opensuse.org points to localhost, so use obs-login
		with socket.create_connection(("obs-login.opensuse.org", 443)) as sock:
			# Not sure which name to use for SNI.
			# HTTP Host: one should take precendence though and we need the right cert
			with context.wrap_socket(sock, server_hostname="obs-login.opensuse.org") as ssock:
				self.relayHttp(ssock, requestline)

class TcpServer(socketserver.ThreadingTCPServer):
	allow_reuse_address = True # Makes testing quicker

try:
	# Start a thread to take care of https requests
	httpd_ssl = TcpServer(('127.0.0.1', 443), RegProxy)
	httpd_ssl.socket = ssl.wrap_socket(httpd_ssl.socket, server_side=True,
			keyfile="regproxy-key.pem", certfile="regproxy-cert.pem")

	_thread.start_new_thread(lambda s: s.serve_forever(), (httpd_ssl,))

	# And do port 80 in the main thread
	TcpServer(('127.0.0.1', 80), RegProxy).serve_forever()
except IOError:
	# For local testing with curl -v -H "Host: registry.opensuse.org" 127.0.0.1:8081
	httpd = TcpServer(('127.0.0.1', 8081), RegProxy).serve_forever()
