from threading import Thread, Event, Lock
from time import *
from ecdsa import SigningKey, VerifyingKey, NIST256p
from hashlib import sha256
from collections import OrderedDict
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import socket
import datetime
import struct
import io
import json
import cv2
import requests
import pprint
import os
import traceback


MAX_Size = 10000

## Verification Node
class NodeV:
    __strNodeName                   :str            # ex) SensorA, SensorB, ...
    __strNodeRole                   :str            # Validator or Sensor
    __pubKeyNode                    :VerifyingKey   # ex) Node's pubkey
    __privKeyNode                   :SigningKey     # priv
    __nInitialNodeNumber            :int        
    __dictReceivedData              :OrderedDict    # (Json) "nodeName" : {"IP": "ipData", "NodeRole" : "role", "PublicKey": "pubkey"}
    __lockThread                    :Lock           # Mutex Lock
    __eventSocket                   :Event
    __listThread                    :list
    __dictReceivedFrames            :dict           # Received Frames "strNodeName" : [Frame, ...]
    
    IV                              :bytearray
    ownIP                           :str
    nPort                           :int
    socketReceived                  :socket
    socketBroadcastSend             :socket

    def __init__(self, strNodeName, ownIP):
        self.__strNodeName = strNodeName
        self.__strNodeRole = 'Validator'
        self.__dictReceivedData = OrderedDict()
        self.__lockThread = Lock()
        self.__eventSocket = Event()
        self.__listThread = list()
        self.__dictReceivedFrames = dict()
        self.IV   = b'0123456789101112'
        self.nPort = 9000
        self.ownIP = ownIP
        self.__nInitialNodeNumber = 0
        self.broadCastIP = ownIP[:3]+"255.255.255"
        self.sendFrameBytes = 1024
        
        # 받고 보낼 소켓 생성
        self.socketReceived = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socketBroadcastSend = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # 보내는 소켓은 BroadCast, 받는 소켓은 전부 수용하도록 설정
        self.socketReceived.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socketReceived.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.socketReceived.bind(('', self.nPort))
        
        self.socketBroadcastSend.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.socketBroadcastSend.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socketBroadcastSend.bind((self.ownIP, 0))
        
    def __image_to_bytes(self, image):
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        return img_byte_arr

    def __broadCastNodeData(self):
        dict_data = {self.__strNodeName : {"IP": self.ownIP, "Role": self.__strNodeRole, "PublicKey" : self.__pubKeyNode}}
        jsonNodeData = json.dumps(dict_data)
    
        if self.__nInitialNodeNumber == 0:
            raise Exception("초기 네트워크 노드 설정이 되어있지 않습니다.")
        
        while True:
            # 특정 갯수에 도달했거나, E type의 메시지가 왔다면 종료.
            self.__lockThread.acquire_lock()
            if len(self.__dictReceivedData) >= self.__nInitialNodeNumber or self.__eventSocket.is_set():
                self.__lockThread.release_lock()
                print(f"Status::NodeList: {len(self.__dictReceivedData)}")
                break
            self.__lockThread.release_lock()
            
            ## 모든 네트워크 대역에 Broadcast
            # B||dictData
            typeSendB = struct.pack('c', b'B')
            message = typeSendB + jsonNodeData.encode('utf-8')
            # 모든 네트워크 대역에 Broadcast
            self.socketBroadcastSend.sendto(message, (self.__broadCastIP, self.nPort))
            sleep(3)

        # 만약 누군가 끝났다고 Packet을 보내지 않았다면 아래를 수행.
        # 초기 노드들이 수집되었다면, 끝을 알리고, 다음을 진행.
        if not self.__eventSocket.is_set():
            typeSendE = struct.pack('c', b'E')
            self.socketBroadcastSend.sendto(typeSendE, (self.__broadCastIP, self.nPort))
        
        # 자신이 가진 데이터를 모두 전송.
        # N||NodeList
        typeSendN = struct.pack('c', b'N')
        dataEncoded = json.dumps(self.__dictReceivedData).encode('utf-8')
        message = typeSendN + dataEncoded
        self.socketBroadcastSend.sendto(message, (self.__broadCastIP, self.nPort))
        
    def __receivedNodeData(self):
        while True:
            self.__lockThread.acquire_lock()
            if self.__dictReceivedData.__len__() >= self.__nInitialNodeNumber:
                self.__lockThread.release_lock()
                break
            self.__lockThread.release_lock()
            
           # type, size check
            initialData, addr = self.socketReceived.recvfrom(4096)
            message_type = struct.unpack('c', initialData[:1])[0]
            # End
            if message_type == b'E':
                print(f"State::{addr}대역의 노드가 초기 네트워크 구성에 성공했습니다.")
                self.__eventSocket.set()
                break
            # Node Information
            elif message_type == b'B':
                jsonData = initialData[1:]
                dictData = json.loads(jsonData.decode('utf-8'))
                self.__dictReceivedData.update(dictData)

        # E 타입의 메시지를 받았다면, N 타입의 패킷을 수용하여, 노드정보 업데이트.
        while True:
            nodeListData, addr = self.socketReceived.recvfrom(10240)
            message_type = struct.unpack('c', nodeListData[:1])[0]
            if message_type == b'N':
                dictNodeData = json.loads(nodeListData[1:].decode('UTF-8'))
                oldDictSize = len(self.__dictReceivedData)
                self.__dictReceivedData.update(dictNodeData)
                print(f"State::업데이트 전 크기: {oldDictSize}, 업데이트 후 크기: {len(self.__dictReceivedData)}")
                break
            else:
                continue
    
    def networkInitialize(self):
        try:
            send_thread = Thread(target=self.__broadCastNodeData)
            recv_thrad = Thread(target=self.__receivedNodeData)
            send_thread.daemon = True
            recv_thrad.daemon = True
            self.__listThread.append(send_thread)
            self.__listThread.append(recv_thrad)
            
            for work in self.__listThread:
                work.start()
            
            for work in self.__listThread:
                work.join()
            print("Done Network Initialized")
            pprint.pprint(self.__dictReceivedData)
        except Exception as e:
            print(f"다음과 같은 오류가 발생했습니다.\n{e}")
            self.__listThread.clear()
            exit(1)
    
    def loadSecrete(self, file):
        with open(file, 'r') as f:
            data = json.load(f)
            dictKeyPair = data[self.__strNodeName]
            priv = list(dictKeyPair.keys())[0]
            bytesPriv = bytes.fromhex(priv)
            ownPriv = SigningKey.from_string(bytesPriv, curve=NIST256p)
            pub = dictKeyPair[priv]
            bytesPub = bytes.fromhex(pub)
            ownPub = VerifyingKey.from_string(bytesPub, curve=NIST256p)

        self.__privKeyNode = ownPriv
        self.__pubKeyNode = ownPub

    def getOwnPrivateKey(self):
        return self.__privKeyNode
    
    def getOwnPublicKey(self):
        return self.__pubKeyNode
        
    def getNodeName(self):
        return self.__strNodeName
    
    def setNodeRole(self, strNodeRole   :str):
        if strNodeRole == "Validator" or strNodeRole == "Sensor":
            self.__strNodeRole = strNodeRole
        else:
            raise Exception("올바르지 않는 Role을 부여했습니다")
        
    def setInitialNodeNumber(self, nNodeNum: int):
        self.__nInitialNodeNumber = nNodeNum
    
    def receivedSensorData(self, strNodeName):
        print(f"{strNodeName}의 Frame을 수신합니다.")
        # 노드의 공개키 찾기 추가하기
        # nodeData = self.__dictReceivedData[strNodeName]
        # if nodeData == None:
        #     raise Exception(f"{strNodeName}은 네트워크에 존재하지 않는 노드이름입니다.")            
        # pubKeyNode  = nodeData['PublicKey']
        # if pubKeyNode == None:
        #     raise Exception(f"{strNodeName}의 공개키가 존재하지 않습니다.")
        
        # testKey = '8063eeafdccd2dd0c6a121824ab966482be2934b02a6bef0112aaa53e9c85c930ff5c701c7493f0190849dfc8f6f7bf9e4f09f044eaf7418adb8bf4ea94fff2a'
        # pubKeyNode=VerifyingKey.from_string(bytes.fromhex(testKey), curve=NIST256p)
        
        listFrameData = list()
        counter = 0
        try:
            while True:
                # S||nFrameList||SID,SIG(F||AddrIPFS),AddrIPFS
                receivedData, addr = self.socketReceived.recvfrom(4096)
                typePacket = struct.unpack('c', receivedData[:1])[0]
                if typePacket != b'S':
                    continue
                
                totalFrames = struct.unpack('Q', receivedData[1:9])[0]
                splitingData = receivedData[9:].decode('UTF-8')
                splitedData = splitingData.split(',')
                if splitedData[0] != strNodeName:
                    continue
                if counter == totalFrames:
                    break
                
                signature = splitedData[1]
                addrIPFS = splitedData[2]
                frame = b''
                while True:
                    receivedFrame, addr = self.socketReceived.recvfrom(self.sendFrameBytes)
                    if receivedFrame == b'E':
                        break
                    frame = frame + receivedFrame
                # with open('reframe.txt', 'w') as f:
                #     f.write(frame.hex())
                
                message = f'{frame}{addrIPFS}'.encode("UTF-8")
                ret = pubKeyNode.verify(bytes.fromhex(signature), message, sha256)
                if not ret:
                    raise Exception(f"{pubKeyNode}의 {addrIPFS}의 서명 검증에 실패했습니다.")
                
                listFrameData.append(frame)
                counter += 1
                print(f'현재:{counter}, 전체:{totalFrames}')
                
            self.__dictReceivedFrames[strNodeName] = listFrameData
            print(f"{strNodeName}의 총 {totalFrames} Frame을 저장하였습니다.")
            
        except Exception as e:
            print(f"{strNodeName}의 데이터를 수집하는 과정에서 아래 오류가 발생했습니다.\n{e}")
        
    def calculateMerkleTree(self, strNodeName):
        listRecedFrame = self.__dictReceivedFrames[strNodeName]
        listHashData = list()
        
        for frame in listRecedFrame:
            listHashData.append(sha256(frame.encode("UTF-8")).digest())
        
        while len(listHashData) != 1:
            if len(listHashData) % 2 != 0:
                listHashData.append(listHashData[-1])
                
            for i in range(len(listHashData//2)):
                left = listHashData.pop(0)
                right = listHashData.pop(0)
                listHashData.append(sha256(f'{left.hex()}{right.hex()}'.encode('UTF-8')).digest())
        
        return listHashData[0].hex()            

## Node Sensor & Verification
class NodeSV(NodeV):
    __strSensorURL          :str
    __ownIPFSUrl            :str
    __dicttSensorData       :dict   #ex) [ "time": {"IPFSAddr": "addr", "Frames": []}, ....]
    __dictTimeKey           :dict   #ex) {"time":"Key"}

    def __init__(self, strNodeName  :str, ownIP, secreteFile ,strURL, strOwnIPFS):
        super().__init__(strNodeName, ownIP)
        self.__strSensorURL = strURL
        self.__ownIPFSUrl = strOwnIPFS
        self.setNodeRole("Sensor")
        self.loadSecrete(secreteFile)
        self.__dicttSensorData = dict()
        
    def __generateToken(self, pubkey):
        nPubkey = len(pubkey.to_string())#len(pubkey)
        randomBytes = os.urandom(nPubkey)
        return randomBytes

    def __uploadSensorDataIPFS(self, fileName):
        url = self.__ownIPFSUrl +'/api/v0/add'
        
        pubkey = self.getOwnPublicKey().to_string()
        token = self.__generateToken(pubkey)
        key = bytes(a ^ b for a, b in zip(pubkey, token))
        cipher = AES.new(key, AES.MODE_CBC, self.__IV)

        with open(fileName, 'rb') as f:
            data = f.read()
        ciphertext = cipher.encrypt(pad(data, AES.block_size))
        
        file = {'file': ciphertext}
        response = requests.post(url, files=file)
        if response.status_code == 200:
            self.__dictTimeKey[fileName] = token
            return json.loads(response.text)
        else:
            raise Exception("영상을 IPFS에 올리지 못했습니다.")
    
    def getSensorData(self, timeDelay):
        # Get Video Data
        timeCurrent = datetime.datetime.now().strftime("%Y-%m-%d.%H:%M:%S")
        
        try:
            cap = cv2.VideoCapture(self.__strSensorURL)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = 40
            # 영상을 내보내는 형식은 avi 형식으로
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            filePath = f'SavedVideo/{timeCurrent}.avi'
            out = cv2.VideoWriter(filePath, fourcc, fps, (width, height))
            
            if not cap.isOpened():
                raise Exception(f"{self.__strSensorURL} 주소에서 데이터를 받을 수 없습니다.")
            
            videoFrame = list()
            start_time = cv2.getTickCount() / cv2.getTickFrequency()
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                ret, buffer = cv2.imencode('.jpg', frame)
                if not ret:
                    raise Exception("받은 Frame을 image로 변경할 수 없습니다.")
                
                byteFrame = buffer.tobytes()
                videoFrame.append(byteFrame)
                out.write(frame)
                
                current_time = cv2.getTickCount() / cv2.getTickFrequency()
                if current_time - start_time >= timeDelay:
                    break
                
            cap.release()
            out.release()
            
            # IPFS 업로드
            #res = self.__uploadSensorDataIPFS(filePath)
            #print(res)
            
            IPFSDataHash = 'aaaa' #res['Hash']
            innerJson = {"IPFSAddr":IPFSDataHash, "Frames": videoFrame}
            
            # "time": {"IPFSAddr": "addr", "Frames": []}
            self.__dicttSensorData[current_time] = innerJson
            return current_time
            
        except Exception as e:
            print(f"다음과 같은 예외가 발생했습니다.\n{e}")

    def sendSensorData(self, timeSensor):
        collectionsSensorData = self.__dicttSensorData[timeSensor]
        addrIPFS = collectionsSensorData['IPFSAddr']
        listFrames = collectionsSensorData['Frames']
        
        typePacket = b'S'
        packedType = struct.pack('c', typePacket)
        nListSensorFrame = len(listFrames)
        packedLengthFrames = struct.pack('Q', nListSensorFrame)
        strNodeName = self.getNodeName()
        
        # S||nFrameList||SID,SIG(F||AddrIPFS),AddrIPFS,Frame
        # S||nFrameList
        bcastmessage = packedType + packedLengthFrames
        
        priv = self.getOwnPrivateKey()
        for frame in listFrames:
            # with open('frame.txt', 'w') as f:
            #     f.write(frame.hex())
            messageSign = f'{frame}{addrIPFS}'.encode("UTF-8")
            sig = priv.sign_deterministic(
                messageSign,
                hashfunc=sha256
            )
            
            # S||nFrameList||SID,SIG(F||AddrIPFS),AddrIPFS
            sendMessage = bcastmessage + f'{strNodeName},{sig.hex()},{addrIPFS}'.encode('UTF-8')
            self.socketBroadcastSend.sendto(sendMessage, (self.broadCastIP, self.nPort))
            
            if len(frame) % self.sendFrameBytes != 0:
                sendCount = len(frame) // self.sendFrameBytes + 1
            else:
                sendCount = len(frame) // self.sendFrameBytes
            
            for i in range(sendCount):
                self.socketBroadcastSend.sendto(frame[i*1024:(i+1)*1024], (self.broadCastIP, self.nPort))
            self.socketBroadcastSend.sendto(b"E", (self.broadCastIP, self.nPort))