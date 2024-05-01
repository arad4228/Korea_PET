from threading import Thread, Event, Lock
from time import *
from ecdsa import SigningKey, VerifyingKey, NIST256p
from hashlib import sha256
import socket
import datetime
import subprocess
import shlex
import struct
import io
import av

MAX_Size = 10000

## Verification Node
class NodeV:
    __pubKeyNode            :VerifyingKey   # ex) Node's pubkey to hex String
    __strNodeRole           :str            # Validator or Sensor
    __privKey               :SigningKey     # priv
    __listNodes             :dict           #(Json) "NodeName" : {"NodeRole" : "role", "Port": "nPort", "Pubkey": "pubkeyes"}
    __nInitialNodeNumber    :int        
    __dictReceivedData      :dict           # (Json) "NodeName" : {"NodeRole" : "role", "Port": "nPort"}
    __lockThread            :Lock           # Mutex Lock
    __listThread            :list
    __listFrames            :dict           # Received Frames "NodeName" : [Frame, ...]

    __socketSendFrame       :socket
    __socketReceived        :socket
    
    def __init__(self, strPubkey, port):
        self.__pubKeyNode = VerifyingKey.from_string(bytes.fromhex(strPubkey), curve=NIST256p)
        self.__strNodeRole = 'Validator'
        self.__listNodes = list()
        self.__dictReceivedData = dict()
        self.__lockThread = Lock()
        self.__listThread = list()
        self.__listFrames = dict()
        
        # 받고 보낼 소켓 생성
        self.__socketSendFrame = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__socketReceived = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 보내는 소켓은 BroadCast, 받는 소캣은 전부 수용하도록 설정
        self.__socketSendFrame.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.__socketReceived.bind(('', port))

    def __image_to_bytes(self, image):
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        return img_byte_arr

    def getNodeName(self):
        return self.__pubKeyNode.to_string().hex()
    
    def setNodeRole(self, strNodeRole   :str):
        if strNodeRole == "Validator" or strNodeRole == "Sensor":
            self.__strNodeRole = strNodeRole
        else:
            raise Exception("올바르지 않는 Role을 부여했습니다")
        
    def setInitialNodeNumber(self, nNodeNum: int):
        self.__nInitialNodeNumber = nNodeNum

    # 수정 필요
    def loadSecrete(self, secrete):
        with open(secrete, 'r') as f:
            data = f.readline()
            # 특정 데이터를 기반으로 데이터를 분리.
            
            self.__privKey = data
    
    def getOwnSecrete(self):
        return self.__privKey
    
    def broadCastNodeData(self, port):
        while True:
            # Lock을 얻고 몇개의 데이터를 가지고 있는지 리스트를 확인
            self.__lockThread.aquire()
            if len(self.__listNodes) >= self.__nInitialNodeNumber:
                self.__lockThread.release()
                break
            self.__lockThread.release()

            ## 모든 네트워크 대역에 Broadcast
            message = (self.pubKeyNode + self.__strNodeRole).encode("UTF-8")
            self.__socketSendFrame.sendto(message, ('<broadcast>', port))

    def receivedNodeData(self):
        while True:
            self.__lockThread.aquire()
            if len(self.__listNodes) >= self.__nInitialNodeNumber:
                self.__lockThread.release()
                break
            self.__lockThread.release()

            len = self.__socketReceived.recv(1)
            # nodeData = NodeName||NodeRole
            nodeData, addr = self.__socketReceived(len)
            splitData = nodeData.split(',')

            self.__lockThread.acquire()
            self.__listNodes[addr] = splitData
            self.__lockThread.release()

    def sendListNodeData(self):
        # BroadCast Node List data;
        # length of Node | key: Ip value: NodeName||NodeRole
        message = str(len(self.__listNodes))
        print('temp')
    
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