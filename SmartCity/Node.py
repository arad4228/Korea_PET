from threading import Thread, Event, Lock
from time import *
from ecdsa import SigningKey, VerifyingKey, NIST256p
from hashlib import sha256
from collections import OrderedDict
import socket
import datetime
import struct
import io
import json
import cv2
import requests
# import av
# import subprocess
# import shlex

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

    __ownIPAddress                  :str
    __nPort                         :int
    __socketReceived                :socket
    __socketBroadcastSendFrame      :socket

    def __init__(self, strNodeName, ownIP):
        self.__strNodeName = strNodeName
        self.__strNodeRole = 'Validator'
        self.__dictReceivedData = OrderedDict()
        self.__lockThread = Lock()
        self.__eventSocket = Event()
        self.__listThread = list()
        self.__dictReceivedFrames = dict()
        self.__nPort = 9000
        self.__ownIPAddress = ownIP
        
        # 받고 보낼 소켓 생성
        self.__socketReceived = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__socketBroadcastSendFrame = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 보내는 소켓은 BroadCast, 받는 소캣은 전부 수용하도록 설정
        self.__socketReceived.bind((ownIP, self.__nPort))
        self.__socketBroadcastSendFrame.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def __image_to_bytes(self, image):
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        return img_byte_arr

    # Test 필요
    def __broadCastNodeData(self):
        dict_data = {self.__strNodeName : {"IP": self.__ownIPAddress, "Role": self.__strNodeRole, "PublicKey" : self.__pubKeyNode}}
        jsonNodeData = json.dumps(dict_data)
        nJsonNodeData = len(jsonNodeData)
        
        while True:
            # 특정 갯수에 도달했거나, E type의 메시지가 왔다면 종료.
            self.__lockThread.aquire()
            if len(self.__dictReceivedData) >= self.__nInitialNodeNumber or self.__eventSocket.is_set():
                self.__lockThread.release()
                print(f"Status::NodeList: {len(self.__dictReceivedData)}")
                break
            self.__lockThread.release()
            
            ## 모든 네트워크 대역에 Broadcast
            # B||Size||dictData
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
        # N||Size||NodeList
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
                print(f"State::{addr}대역의 노드가 초기 네트워크 구성에 성공했습니다.")
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
            oldDictSize = len(self.__dictReceivedData)
            self.__dictReceivedData.update(dictNodeData)
            print(f"State::업데이트 전 크기: {oldDictSize}, 업데이트 후 크기: {len(self.__dictReceivedData)}")
        # 수정 필요
    
    def networkInitialize(self):
        self.__listThread.append(Thread(target=self.__broadCastNodeData))
        self.__listThread.append(Thread(target=self.__receivedNodeData))
        
        for work in self.__listThread:
            work.start()
        
        for work in self.__listThread:
            work.join()
    
    def loadSecrete(self, file):
        with open(file, 'r') as f:
            data = json.load(f)
            dictKeyPair = data[self.__strNodeName]
            priv = list(dictKeyPair.keys())[0]
            pub = dictKeyPair[priv]
            self.__privKeyNode = priv
            self.__pubKeyNode = pub
                
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
        nodeData = self.__dictReceivedData[strNodeName]
        if nodeData == None:
            raise Exception(f"{strNodeName}은 네트워크에 존재하지 않는 노드이름입니다.")            
        pubKeyNode  = nodeData['PublicKey']
        if pubKeyNode == None:
            raise Exception(f"{strNodeName}의 공개키가 존재하지 않습니다.")
        
        listFrameData = list()
        counter = 0
        try:
            while True:
                typePacket = self.__socketReceived(1)
                typePacket = struct.unpack('c', typePacket[0])
                if typePacket != b'S':
                    continue
                # S||nFrameList||nData||SID,SIG(F||AddrIPFS),Frame,AddrIPFS

                totalFrames = self.__socketReceived.recv(8)
                totalFrames = struct.unpack('Q', totalFrames[0])
                nFrameSize = self.__socketReceived.recv(8)
                nFrameSize = struct.unpack('Q', nFrameSize[0]) # long long
                
                recevedData = self.__socketReceived.recv(nFrameSize)
                splitedData = recevedData.split(',')
                if splitedData[0] != strNodeName:
                    continue
                if counter == totalFrames:
                    break
                
                signature = splitedData[1]
                frame = splitedData[2]
                addrIPFS = splitedData[3]
                message = f'{frame}{addrIPFS}'.encode("UTF-8")
                ret = pubKeyNode.verify(signature, message, sha256)
                if not ret:
                    raise Exception(f"{pubKeyNode}의 {addrIPFS}의 서명 검증에 실패했습니다.")
                
                listFrameData.append(frame)
                counter += 1
                
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
    __dicttSensorData        :dict   #ex) [ "time": {"IPFSAddr": "addr", "Frames": []}, ....]

    def __init__(self, strNodeName  :str, ownIP, secreteFile ,strURL, strOwnIPFS):
        super().__init__(strNodeName, ownIP)
        self.__strSensorURL = strURL
        self.__ownIPFSUrl = strOwnIPFS
        self.setNodeRole("Sensor")
        self.loadSecrete(secreteFile)
        self.__dicttSensorData = dict()
        
    def __uploadSensorDataIPFS(self, fileName):
        url = self.__ownIPFSUrl +'/api/v0/add'
        file = {'file': open(fileName, 'rb')}
        response = requests.post(url, files=file)
        if response.status_code == 200:
            return json.loads(response.text)
        else:
            raise Exception("영상을 IPFS에 올리지 못했습니다.")
    
    def getSensorData(self, timeDelay):
        # Get Video Data
        timeCurrent = datetime.datetime.now().strftime("%Y-%m-%d.%H:%M:%S")
        # command = f"ffmpeg -i {shlex.quote(self.__strSensorURL)} -t {timeDelay} -c copy {shlex.quote(f'{self.getNodeName()} {timeCurrent}.mp4')}"
        # try:
        # # subprocess를 사용하여 타임아웃 설정
        #     process = subprocess.run(command, shell=True, timeout=timeDelay+5, text=True, capture_output=True)
        #     if process.returncode != 0:
        #         raise Exception(f"{self.getNodeName()}의 {timeCurrent}시간대 영상 저장 실패")
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
                videoFrame.append(frame)
                out.write(frame)
                
                current_time = cv2.getTickCount() / cv2.getTickFrequency()
                if current_time - start_time >= timeDelay:
                    break
                
            cap.release()
            out.release()
            # IPFS 업로드
            res = self.__uploadSensorDataIPFS(filePath)
            print(res)
            IPFSDataHash = res['Hash']
            innerJson = {"IPFSAddr":IPFSDataHash, "Frames": videoFrame}
            
            # "time": {"IPFSAddr": "addr", "Frames": []}
            self.__dicttSensorData[current_time] = innerJson
            return current_time
            
        except Exception as e:
            print(f"다음과 같은 예외가 발생했습니다. \n{e}")

    def sendSensorData(self, timeSensor):
        collectionsSensorData = self.__dicttSensorData[timeSensor]
        addrIPFS = collectionsSensorData['IPFSAddr']
        listFrames = collectionsSensorData['Frames']
        
        typePacket = b'S'
        packedType = struct.pack('c', typePacket)
        nListSensorFrame = len(listFrames)
        packedLengthFrames = struct.pack('Q', nListSensorFrame)
        strNodeName = self.getNodeName()
        nSID = struct.pack('i', len(strNodeName))
        # S||nFrameList||nData||SID,SIG(F||AddrIPFS),Frame,AddrIPFS
        # S||nFrameList||nSID
        bcastmessage = packedType + packedLengthFrames
        
        priv = self.getOwnPrivateKey()
        for frame in listFrames:
            messageSign = f'{frame}{addrIPFS}'.encode("UTF-8")
            sig = priv.sign_deterministic(
                message = messageSign,
                hashfunc=sha256
            )
            
            sendMessage = bcastmessage + f'{strNodeName},{sig},{frame},{addrIPFS}'
            self.__socketBroadcastSendFrame.sendto(sendMessage, ('<broadcast>', self.__nPort))
            