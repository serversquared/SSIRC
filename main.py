import socket
import json
import multiprocessing
import sys
import time
import argparse

# Default server settings. Changeable via command-line options.
default_bound_ip = ''		# IP to bind to (or blank string for all).
default_bound_port = 6667	# Port to bind to (or 0 for random).
default_buffer_size = 1024	# Packet buffer size (power of 2).
default_timeout = 10		# Client timeout in seconds (or 0 to block).
default_max_clients = 32	# Total number of clients allowed.
default_max_clients_per_ip = 4	# Number of clients allowed per IP address.
default_server_delay = 0.02	# Time in seconds to delay various server operations.

def client_handler(*args, **kwargs):
	pass

def server_thread(*args, **kwargs):
	pass

def server_handler(settings):
	try:
		q = multiprocessing.Queue()
		server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		server.settimeout(None)
		server.bind((settings['bound_ip'], settings['bound_port']))
		server.listen(1)
		server_ip, server_port = server.getsockname()
		print('[{}] Server bound to {}:{}'.format(int(time.time()), server_ip, server_port))

		thread = multiprocessing.Process(target=server_thread, args=(settings, server, q))
		thread.daemon = False
		thread.start()

		while True:
			pass

	finally:
		pass

def main():
	parser = argparse.ArgumentParser(description='(server)^2 IRC')
	parser.add_argument('-a', '--address', type=str, metavar='IP', dest='bound_ip', help='address to bind to', action='store', default=default_bound_ip)
	parser.add_argument('-p', '--port', type=int, metavar='PORT', dest='bound_port', help='port to bind to', action='store', default=default_bound_port)
	parser.add_argument('-b', '--buffer', type=int, metavar='BYTES', dest='buffer_size', help='size of network buffer in bytes', action='store', default=default_buffer_size)
	parser.add_argument('-t', '--timeout', type=int, metavar='SECONDS', dest='timeout_seconds', help='timeout in seconds or 0 to block', action='store', default=default_timeout)
	parser.add_argument('-m', '--max-clients', type=int, metavar='CLIENTS', dest='max_clients', help='total number of clients allowed', action='store', default=default_max_clients)
	parser.add_argument('-c', '--clients-per-ip', type=int, metavar='CLIENTS', dest='max_clients_per_ip', help='max number of clients allowed per address', action='store', default=default_max_clients_per_ip)
	parser.add_argument('-D', '--server-delay', type=float, metavar='SECONDS', dest='server_delay', help='time in seconds to delay verious server operations', action='store', default=default_server_delay)
	settings = vars(parser.parse_args())
	if settings['timeout_seconds'] < 1:	settings['timeout_seconds'] = None
	server_handler(settings)

if __name__ == '__main__':
	try:
		main()
	except KeyboardInterrupt:
		pass
	finally:
		pass
