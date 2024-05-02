from threading import Thread, Event, Lock
from time import *
from ecdsa import SigningKey, VerifyingKey, NIST256p
from hashlib import sha256
from collections import OrderedDict
import socket
import datetime
import subprocess
import shlex
import struct
import io
import json
import av

MAX_Size = 10000

## Verification Node
class NodeV:
    __pubKeyNode                    :VerifyingKey   # ex) Node's pubkey to hex String
    __strNodeRole                   :str            # Validator or Sensor
    __privKey                       :SigningKey     # priv
    __nInitialNodeNumber            :int        
    __dictReceivedData              :OrderedDict    # (Json) "pubkeyNode" : {"IP": "ipData", "NodeRole" : "role"}
    __lockThread                    :Lock           # Mutex Lock
    __eventSocket                   :Event
    __listThread                    :list
    __listFrames                    :dict           # Received Frames "pubkeyNode" : [Frame, ...]

    __ownIPAddress                  :str
    __nPort                         :int
    __socketReceived                :socket
    __socketBroadcastSendFrame      :socket

    def __init__(self, strPubkey, ownIp):
        self.__pubKeyNode = VerifyingKey.from_string(bytes.fromhex(strPubkey), curve=NIST256p)
        self.__strNodeRole = 'Validator'
        self.__dictReceivedData = OrderedDict()
        self.__lockThread = Lock()
        self.__eventSocket = Event()
        self.__listThread = list()
        self.__listFrames = dict()
        self.__nPort = 8080
        self.__ownIPAddress = ownIp
        
        # 받고 보낼 소켓 생성
        self.__socketReceived = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__socketBroadcastSendFrame = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 보내는 소켓은 BroadCast, 받는 소캣은 전부 수용하도록 설정
        self.__socketReceived.bind((ownIp, self.__nPort))
        self.__socketBroadcastSendFrame.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def __image_to_bytes(self, image):
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        return img_byte_arr

    # Test 필요
    def __broadCastNodeData(self, port):
        dict_data = {"pubkeyNode" : {"IP": f"{self.__ownIPAddress}", "Role": f"{self.__strNodeRole}"}}
        jsonNodeData = json.dumps(dict_data)
        nJsonNodeData = len(jsonNodeData)
        
        while True:
            # 특정 갯수에 도달했거나, E type의 메시지가 왔다면 종료.
            self.__lockThread.aquire()
            if len(self.__dictReceivedData) >= self.__nInitialNodeNumber or self.__eventSocket.is_set():
                self.__lockThread.release()
                break
            self.__lockThread.release()
            ## 모든 네트워크 대역에 Broadcast
            # B||Size||
            typeSendB = struct.pack('c', b'B')
            nData = struct.pack('Q', nJsonNodeData)
            message = typeSendB + nData + jsonNodeData.encode('utf-8')
            
            # 모든 네트워크 대역에 Broadcast
            self.__socketBroadcastSendFrame.sendto(message, ('<broadcast>', self.__nPort))

        # 만약 누군가 끝났다고 Packet을 보내지 않았다면 아래를 수행.
        # 초기 노드들이 수집되었다면, 끝을 알리고, 다음을 진행.
        if not self.__eventSocket.is_set():
            typeSendE = struct.pack('c', b'E')
            self.__socketBroadcastSendFrame.sendto(typeSendE ('<broadcast>', self.__nPort))
        
        # 자신이 가진 데이터를 모두 전송.
        nData = len(self.__dictReceivedData)
        typeSendN = struct.pack('c', b'N')
        nMessageData = struct.pack('Q', nData)
        dataEncoded = json.dumps(self.__dictReceivedData).encode('utf-8')
        message = typeSendN + nMessageData + dataEncoded
        self.__socketBroadcastSendFrame.sendto(message, ('<broadcast>', self.__nPort))
        
    # Test 필요.
    def __receivedNodeData(self):
        while True:
            self.__lockThread.aquire()
            if len(self.__dictReceivedData) >= self.__nInitialNodeNumber:
                self.__lockThread.release()
                break
            self.__lockThread.release()

           # type, size check
            initialData, addr = self.__socketReceived.recvfrom(9)
            message_type = struct.unpack('c', initialData[:1])[0]
            # End
            if message_type == b'E':
                self.__eventSocket.set()
                break
            # Node Information
            elif message_type == b'B':
                nData = struct.unpack('Q', initialData[1:])[0]
                jsonData, addr = self.__socketReceived.recvfrom(nData)
                dictData = json.loads(jsonData.decode('utf-8'))
                self.__dictReceivedData = self.__dictReceivedData.update(dictData)
        
        # E 타입의 메시지를 받았다면, N 타입의 패킷을 수용하여, 노드정보 업데이트.
        typeData, addr = self.__socketReceived.recvfrom(1)
        message_type = struct.unpack('c', typeData)[0]
        if message_type == b'N':
            nData, addr = self.__socketReceived.recvfrom(8)
            nData = struct.unpack('Q', nData)[0]
            dictNodeData, addr = self.__socketReceived.recvfrom(nData)
            dictNodeData = json.loads(dictNodeData.decode('UTF-8'))
            
        # 수정 필요
    def loadSecrete(self, secrete):
        with open(secrete, 'r') as f:
            data = f.readline()
            # 특정 데이터를 기반으로 데이터를 분리.
            
            self.__privKey = data
    
    def getOwnSecrete(self):
        return self.__privKey
        
    def getNodeName(self):
        return self.__pubKeyNode.to_string().hex()
    
    def setNodeRole(self, strNodeRole   :str):
        if strNodeRole == "Validator" or strNodeRole == "Sensor":
            self.__strNodeRole = strNodeRole
        else:
            raise Exception("올바르지 않는 Role을 부여했습니다")
        
    def setInitialNodeNumber(self, nNodeNum: int):
        self.__nInitialNodeNumber = nNodeNum

    def initialized(self):
        print("temp")
    
    def receivedSensorData(self, pubKeyNode):
        try:
            listFrameData = list
            totalFrames = self.__socketReceived.recv(4)
            totalFrames = struct.unpack('i', totalFrames[0])
            print(f"{pubKeyNode}의 총 {totalFrames} Frame을 수신합니다.")
            counter = 0
            while True:
                if counter == totalFrames:
                    break
                nFrameSize = self.__socketReceived.recv(8)
                nFrameSize = struct.unpack('Q', nFrameSize[0]) # long long
                
                # SID(pubKeyNode),SIG(F||Addr(s,t)),F,Addr <- 전제는 String으로 보내기.
                recevedData = self.__socketReceived.recv(nFrameSize)
                splitedData = recevedData.split(',')
                if splitedData[0] != pubKeyNode:
                    continue
                signature = splitedData[1]
                frame = splitedData[2]
                addrIPFS = splitedData[3]
                message = f'{frame},{addrIPFS}'
                ret = pubKeyNode.verify(signature, message, sha256)
                if not ret:
                    raise Exception(f"{pubKeyNode}의 {addrIPFS}의 서명 검증에 실패했습니다.")
                
                listFrameData.append(frame)
                counter += 1
                
            self.__dictReceivedData[pubKeyNode] = listFrameData
            print(f"{pubKeyNode}의 총 {totalFrames} Frame을 저장하였습니다.")
            
        except Exception as e:
            print(f"{pubKeyNode}의 데이터를 수집하는 과정에서 아래 오류가 발생했습니다.\n{e}")
        
    def calculateMerkleTree(self, pubKeyNode):
        listNodeFrame = self.__dictReceivedData[pubKeyNode]
        listHashData = list()
        

## Node Sensor & Verification
class NodeSV(NodeV):
    __strSensorURL          :str
    __listSensorFrame       :list

    def __init__(self, strPubkey  :str, port, strURL):
        super().__init__(strPubkey, port)
        self.__strSensorURL = strURL
        self.setNodeRole("Sensor")
        self.__listSensorFrame = list()
    
    def getSensorData(self, timeDelay):
        # Get Video Data
        timeCurrent = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        command = f"ffmpeg -i {shlex.quote(self.__strSensorURL)} -t {timeDelay} -c copy {shlex.quote(f'{self.getNodeName()} {timeCurrent}.mp4')}"
        try:
        # subprocess를 사용하여 타임아웃 설정
            process = subprocess.run(command, shell=True, timeout=timeDelay+5, text=True, capture_output=True)
            if process.returncode != 0:
                raise Exception(f"{self.getNodeName()}의 {timeCurrent}시간대 영상 저장 실패")
        except Exception as e:
            print(f"다음과 같은 예외가 발생했습니다. \n{e}")

    def snedSensorData(self):
        print("f")      # 수정