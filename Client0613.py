import socket
import threading
import json
import base64
import os
import time
import cv2
import signal

class SocketClient:
    def __init__(self, client_name, server_ip, server_port):
        self.msg = []
        self.error_msg = None
        self.error_msg_list = {}
        self.image_chunks = {}
        self.client_socket = None
        self.client_name = client_name
        self.server_ip = server_ip
        self.server_port = server_port
        self.stop_event = threading.Event()
        # self.current_time_live = {}
        self.recvive = {}
        print(client_name, server_ip, server_port)

    def client_program(self):
        """
        建立連接
        """
        while not self.stop_event.is_set():
            if self.client_name == "":
                print('名稱設定為空')
                break
            else:
                try:
                    self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    server_address = (self.server_ip, self.server_port)
                    self.client_socket.connect(server_address)
                    self.client_socket.send(self.client_name.encode('utf-8'))
                    self.receive = threading.Thread(target=self.receive_messages)
                    self.receive.start()
                    # self.client_socket.settimeout(5)
                    break
                except socket.error as e:
                    print(f"Connection error: {e}")
                    self.close_socket()                   

    def receive_messages(self):
        """
        接收資料
        """
        while not self.stop_event.is_set():
            # try:
                message = self.client_socket.recv(65536).decode('utf-8')
                # print(message)
                if message:
                    json_data = json.loads(message)
                    self.handle_received_message(json_data)
            # except (socket.timeout, socket.error) as e:
            #     print(f"Socket error: {e}")
            #     self.close_socket()
            #     break
            # except json.JSONDecodeError as e:
            #     print(f"JSON decode error: {e} {message}")
            # except Exception as e:
            #     print(f"Error receiving message: {e} {message}")
            #     break

    def handle_received_message(self, json_data):
        """
        處理資料
        """
        # 根據json_data的內容進行處理
        # if 'state' in json_data:
        #     if json_data['state'] == 'start':
        #         threading.Thread(target=self.judgment_of_data_completeness, args=(json_data['current_time'],)).start()
        #         self.current_time_live[json_data['current_time']] = 'start'
        #     elif json_data['state'] == 'end':
        #         self.current_time_live[json_data['current_time']] = 'end'
                
        if 'error' in json_data:
            
            if json_data["error"] == "resend_image":
                if "timestamp" in json_data:
                    self.error_msg_list[json_data['timestamp']] = "resend_image"
                    print(self.error_msg_list)
                
            if 'reset' in json_data:
                if json_data['reset'] == "image":
                    try:
                        del self.image_chunks[json_data['timestamp']]
                    except:
                        # print(f'沒有 {json_data["timestamp"]}')
                        pass
                
        # if json_data.get('target') == self.client_name:
        #     pass
        
        if "check_result" in json_data:
            for i in range(len(self.msg)):
                self.msg[i] = json_data['check_result']
            
        if 'Final' in json_data:
            self.save_object_coordinate(json_data)
            if not os.path.exists(f"./picture/{json_data['工單編號']}"):
                os.makedirs(f"./picture/{json_data['工單編號']}")
            with open(f"./picture/{json_data['工單編號']}/{json_data['工單編號']}_Result.json", 'w', encoding='utf-8') as file:
                json.dump(json_data, file, ensure_ascii=False, indent=4)
        
        if 'data' in json_data:        
            if json_data['data'] == "image":
                json_data_return = {
                    "receive": "next",
                    "timestamp": json_data['timestamp']
                }
                self.send_json_to_server(json_data_return, json_data["source"])
            
        if 'receive' in json_data:
            self.recvive[json_data['timestamp']] = True
                
        elif 'form' in json_data:
            if json_data['statu'] == 'End':
                if 'image_order_id' in json_data and 'form' in json_data:
                    if not os.path.exists(f"./picture/{json_data['image_order_id']}"):
                        os.makedirs(f"./picture/{json_data['image_order_id']}")
                    # self.save_image_from_base64(''.join(self.image_chunks), f"./picture/{json_data['image_order_id']}/{json_data['form']}.png")
                    self.save_image_from_base64(self.image_chunks[json_data['timestamp']], f"./picture/{json_data['image_order_id']}/{json_data['form']}.png")
                else:
                    # self.save_image_from_base64(''.join(self.image_chunks), 'received_image.jpg')
                    self.save_image_from_base64(self.image_chunks[json_data['timestamp']], 'received_image.jpg')
                print(f"收到圖片了 {str(json_data['timestamp'])} {len(self.image_chunks)}")
                # self.image_chunks.clear()
                del self.image_chunks[json_data['timestamp']]
            elif json_data['statu'] == 'Transmitting':
                # self.image_chunks[json_data['timestamp']].append(json_data['Split_data'])
                if json_data['timestamp'] in self.image_chunks:
                    self.image_chunks[json_data['timestamp']] = self.image_chunks[json_data['timestamp']] + json_data['Split_data']
                else:
                    self.image_chunks[json_data['timestamp']] = json_data['Split_data']
        # else:
        #     if 'target' in json_data:
        #         del json_data['target']
        #     with open('received_data.json', 'w', encoding='utf-8') as file:
        #         json.dump(json_data, file, ensure_ascii=False, indent=4)

    def send_json_to_server(self, json_data, target_name):
        """
        將資料傳送給伺服器
        """
        try:
            json_data["target"] = target_name
            json_data["source"] = self.client_name
            message = json.dumps(json_data)
            self.client_socket.send(message.encode('utf-8'))
        except Exception as e:
            print(f"Error sending JSON: {e}")

    def send_json(self, json_file_path, target_name):
        """
        處理要發送的資料
        """
        try:
            current_time = time.time()
            self.send_json_of_start(target_name, current_time)
            with open(json_file_path, 'r', encoding='utf-8') as file:
                json_data = json.load(file)
            json_data["data"] = "json"
            json_data["current_time"] = current_time
            self.send_json_to_server(json_data, target_name)
            self.send_json_of_end(target_name, current_time)
        except Exception as e:
            print(f"Error reading JSON file: {e}")

    def send_image(self, target_name, image, state):
        """
        發送圖片
        """
        try:
            retval, buffer = cv2.imencode('.jpg', image)
            image_data = base64.b64encode(buffer).decode('utf-8')
            chunk_size = 32768
            current_time = time.time()
            self.send_json_of_start(target_name, current_time)
            
            time.sleep(0.5)
            
            number = 0
            time_current = float(time.time())
            self.recvive[time_current] = False
            for i in range(0, len(image_data), chunk_size):
                chunk_data = image_data[i:i + chunk_size]
                json_data = {
                    "timestamp": time_current,
                    "data": "image",
                    "form": f"image_{state}",
                    "statu": "Transmitting",
                    "Split_data": chunk_data,
                    "number": number
                }
                self.send_json_to_server(json_data, target_name)
                number = number + 1
                while True:
                    if self.recvive[time_current] == True:
                        self.recvive[time_current] = False
                        break
                
                    if time_current in self.error_msg_list:
                        del self.error_msg_list[time_current]
                        self.image_chunks.clear()
                        print("重傳")
                        time.sleep(1)
                        return self.send_image(target_name, image, state)
            json_data = {
                "timestamp": time_current,
                "data": "image",
                "form": f"image_{state}",
                "statu": "End",
                "Split_data": "",
            }
            print(float(time.time()) - time_current)
            # print(time_current)
            # print(self.error_msg_list)
            self.send_json_to_server(json_data, target_name)
            self.send_json_of_end(target_name, current_time)
        except Exception as e:
            print(f"Error sending image: {e}")
            
    def send_image_thread(self, target_name, image, state):
        threading.Thread(target=self.send_image, args=(target_name, image, state)).start()

    def save_image_from_base64(self, image_data, output_file_path):
        """
        儲存圖片
        """
        try:
            image_bytes = base64.b64decode(image_data)
            with open(output_file_path, 'wb') as image_file:
                image_file.write(image_bytes)
        except Exception as e:
            print(f"Error saving image: {e}")

    def close_socket(self):
        """
        關閉伺服器
        """
        self.stop_event.set()  # Set the event to signal the receive_messages thread to stop
        if self.client_socket:
            self.client_socket.close()

    def save_object_coordinate(self, json_data):
        """
        唯翰會用到的資料處理
        """
        with open('./workdata/object.json', 'r', encoding='utf-8') as file:
            assets = json.load(file)

        object_dict = {}
        for item_name, details in assets.items():
            for detail in details:
                if detail.startswith("財產編號："):
                    property_number = detail.split("：")[1]
                    object_dict[item_name] = property_number

        # 更新物件座標及圖片 URL
        for i in object_dict:
            if object_dict[i] == json_data["物品ID"][0].split('：')[1]:
                print(i)
                # 物件的目前座標 json
                with open('./workdata/data.json', 'r', encoding='utf-8') as file:
                    object_mb = json.load(file)

                # 更新座標
                object_mb[i]["目前座標"] = json_data["動作內容"]['目標']

                # 添加圖片 URL
                image_url = f"./picture/{json_data['工單編號']}/image_end.png"
                object_mb[i]["圖片URL"] = image_url

        # 保存更新後的資料
        with open('./workdata/data.json', 'w', encoding='utf-8') as file:
            json.dump(object_mb, file, ensure_ascii=False, indent=4)

    def get_message(self, number):     
        msg = self.msg[number]
        self.msg[number] = None
        return msg

    # def get_error_massage(self):
    #     error_msg = self.error_msg
    #     self.error_msg = None
    #     return error_msg   

    def signal_handler(self, sig, frame):
        print("Interrupt received, stopping...")
        self.close_socket()
        exit(0)

    # def run(self):
    #     try:
    #         self.client_program()
    #         while not self.stop_event.is_set():
    #             time.sleep(1)
    #     except KeyboardInterrupt:
    #         self.close_socket()
    #     finally:
    #         self.close_socket()
    
    def send_json_of_start(self, target, current_time):
        json_data = {
            'state':'start',
            'current_time': current_time,
            'data': 'time_record'
        }
        self.send_json_to_server(json_data, target)
        
    def send_json_of_end(self, target, current_time):
        json_data = {
            'state':'end',
            'current_time': current_time,
            'data': 'time_record'
        }
        self.send_json_to_server(json_data, target)
        
    # def judgment_of_data_completeness(self, current_time):
    #     time.sleep(5)
    #     if self.current_time_live[current_time] == 'start':
    #         print('資料未完整')
    #     elif self.current_time_live[current_time] == 'end':
    #         print('資料完整')
        
        


if __name__ == "__main__":
    try:
        client_class = SocketClient("Kang", "192.168.178.151", 12345)
        thread = threading.Thread(target=client_class.run)  # 注意：這裡不要調用 run() 方法
        thread.start()
        
        while True:
            input("test")
            client_class.send_json('test.json', 'name1')
    except  KeyboardInterrupt:
        client_class.close_socket()  
    
