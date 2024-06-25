import time
import socket
import threading
import json

clients = {}
addresses = {}

def handle_client(client_socket):
    while True:
        try:
            message = client_socket.recv(65536).decode('utf-8')
            # print(client_socket.getpeername())
            if message:
                json_data = json.loads(message)
                print(f"{addresses[client_socket]} 傳送給 {json_data['target']}")
                target = json_data.get("target")
                if target and target in clients:
                    send_json_to_client(clients[target], json_data)
                # print(json_data)
                threading.Thread(target=save_json, args=(json_data,)).start()
                    
                # else:
                #     broadcast(message, client_socket)
            # else:
            #     remove(client_socket)
            #     break
        except (ConnectionResetError, ConnectionAbortedError) as e:
            print(f"Error: {e}")
            remove(client_socket)
            break
        except socket.error as e:
            print(f"socket_Error: {e}")
            remove(client_socket)
            break
        except json.decoder.JSONDecodeError as e:
            print(f"Error: {e}")
            # for client in addresses:
            #     if client_socket == client:
            data = {
                'error': f'resend_{json_data["data"]}'
            }
            
            if 'timestamp' in json_data:
                data['timestamp'] = json_data['timestamp']
                send_json_to_client(client_socket, data)
                if json_data['data'] == "image":
                    data['reset'] = "image"
                    send_json_to_client(clients[json_data['target']], data)
            print(data)
            print(len(json_data))
                    
            
def save_json(json_data):
    with open('received_data.json', 'w', encoding='utf-8') as file:
        json.dump(json_data, file, ensure_ascii=False, indent=4)   

def print_user(): 
    for client in clients:
        print(client)

def broadcast(message, connection):
    for client in clients.values():
        if client != connection:
            try:
                client.send(message.encode('utf-8'))
            except Exception as e:
                print(f"Error broadcasting: {e}")
                remove(client)

def remove(connection):
    for name, client in list(clients.items()):
        if client == connection:
            print(f"Removing client {name} {client.getpeername()}")
            del clients[name]
            connection.close()
            break

def send_json_to_client(client_socket, json_data):
    try:
        message = json.dumps(json_data)
        client_socket.send(message.encode('utf-8'))
        print(f"Sent to {client_socket.getpeername()}")
    except Exception as e:
        print(f"Error sending JSON: {e}")

def server_program(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f'Socket伺服器已啟動 IP:{host}, Port:{port}')

    while True:
        try:
            client_socket, client_address = server_socket.accept()
            name = client_socket.recv(1024).decode('utf-8')
            if name == '':
                print(f'客戶端名稱為空')
                remove(client_socket)
            else:
                clients[name] = client_socket
                addresses[client_socket] = name
                print(f"ID:{name} address:{client_address} 已連接")

                thread = threading.Thread(target=handle_client, args=(client_socket,))
                thread.start()
        except ConnectionResetError as e:
            print(f'客戶端名稱為空 {e}')

def send_json_to_target(target_name, json_data):
    json_data['target'] = target_name
    if target_name in clients:
        try:
            send_json_to_client(clients[target_name], json_data)
        except Exception as e:
            print(f"Error sending JSON data: {e}")
    else:
        print(f"{target_name} 未有此用戶")

if __name__ == "__main__":
    host = "192.168.178.151"
    port = 12345
    server_thread = threading.Thread(target=server_program, args=(host, port))
    server_thread.start()

    # 示例：手動輸入 JSON 數據並發送到指定客戶端
    time.sleep(1)
    while True:
        target_name = input("Enter target client name: ")
        if target_name == "user":
            print_user()
            
        else:
            with open("test.json", "r", encoding='utf-8') as log_file:
                log_data = json.load(log_file)
            send_json_to_target(target_name, log_data)
