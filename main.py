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

def safe_string(dangerous_string):
	return dangerous_string.replace('\n', '\\n').replace('\r', '\\r').replace('\033[', '[CSI]').replace('\033', '[ESC]')

def search_queue(q, key):
	mismatched = []
	matched = None
	while not q.empty():
		item = q.get()
		if type(item) is list and type(item[0]) is str:
			data = json.loads(item[0])
			if key in data:
				matched = data
				break
			else:
				mismatched.append(item)
		else:
			# This means the item is invalid but we'll shove it back in anyways.
			mismatched.append(item)
	for i in range(len(mismatched)):
		q.put(mismatched[i])
	return matched

def replace_queue_item(settings, q, key, value):
	data = None
	while not type(data) is dict:
		time.sleep(settings['server_delay'])
		data = search_queue(q, key)
	data[key] = value
	q.put([json.dumps(data)])

def get_client_tracker(settings, q, peer_name=None):
	data = None
	while not type(data) is dict:
		time.sleep(settings['server_delay'])
		data = search_queue(q, 'connected_clients')
	q.put([json.dumps(data)])
	if not peer_name:
		return data['connected_clients']
	else:
		if peer_name[0] in data:
			return data[peer_name[0]]
		else:
			return False

def update_tracked_client(settings, q, peer_name, remove=False):
	data = None
	while not type(data) is dict:
		time.sleep(settings['server_delay'])
		data = search_queue(q, 'connected_clients')
	if not peer_name[0] in data:
		data[peer_name[0]] = 1
	elif not remove:
		data[peer_name[0]] += 1
	elif remove:
		if data[peer_name[0]] <= 1:
			del data[peer_name[0]]
		else:
			data[peer_name[0]] -= 10
	q.put([json.dumps(data)])

def client_thread(*args, **kwargs):
	pass

def server_thread(settings, server, q):
	try:
		while True:
			connected_clients = get_client_tracker(settings, q)
			if connected_clients < settings['max_clients']:
				client, client_from = server.accept()
				if get_client_tracker(settings, q, client_from) < settings['max_clients_per_ip']:
					q.put([json.dumps({'event': 'client_connect', 'client_from': client_from})])
					client.settimeout(settings['timeout_seconds'])

					thread = multiprocessing.Process(target=client_thread, args=(settings, client, q))
					thread.daemon = True
					thread.start()
				else:
					#Client is connected, but we don't want them.
					q.put([json.dumps({'event': 'client_reject', 'client_from': client_from, 'reason': 'too many connections'})])
					client.shutdown(socket.SHUT_RDWR)
					client.close()
			else:
				try:
					server.settimeout(0.1)
					client, client_from = server.accept()
					# Client is connected, but we don't want them.
					q.put([json.dumps({'event': 'client_reject', 'client_from': client_from, 'reason': 'server full'})])
					client.shutdown(socket.SHUT_RDWR)
					client.close()
				except timeout:
					pass
				finally:
					server.settimeout(None)

			time.sleep(settings['server_delay'])
	except KeyboardInterrupt:
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

		connected_clients = 0
		q.put([json.dumps({'connected_clients': connected_clients})])

		thread = multiprocessing.Process(target=server_thread, args=(settings, server, q))
		thread.daemon = False
		thread.start()

		while True:
			data = search_queue(q, 'event')
			if data:
				if data['event'] == 'client_connect':
					connected_clients += 1
					update_tracked_client(settings, q, data['client_from'], False)
					print('[{}] {}: Connected on port {} ({}/{})'.format(int(time.time()), data['client_from'][0], data['client_from'][1], connected_clients, settings['max_clients']))
				elif data['event'] == 'rx_data':
					print('[{}] {}:{} -> {}'.format(int(time.time()), data['client_from'][0], data['client_from'][1], data['data']))
				elif data['event'] == 'tx_data':
					print('[{}] {}:{} <- {}'.format(int(time.time()), data['client_from'][0], data['client_from'][1], data['data']))
				elif data['event'] == 'client_disconnect':
					connected_clients -= 1
					update_tracked_client(settings, q, data['client_from'], True)
					print('[{}] {}: Disconnected from port {} ({}/{})'.format(int(time.time()), data['client_from'][0], data['client_from'][1], connected_clients, settings['max_clients']))
				elif data['event'] == 'client_reject':
					print('[{}] {}: Rejected from port {} ({})'.format(int(time.time()), data['client_from'][0], data['client_from'][1], data['reason']))

			replace_queue_item(settings, q, 'connected_clients', connected_clients)
			time.sleep(settings['server_delay'])

	finally:
		server.shutdown(socket.SHUT_RDWR)
		server.close()
		print('\nServer closed.')

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
