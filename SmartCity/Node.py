from threading import Thread, Event, Lock
from time import *
from ecdsa import SigningKey, VerifyingKey, NIST256p
from hashlib import sha256
from collections import OrderedDict
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from pprint import pprint
from web3 import Web3
from datetime import datetime
import socket
import struct
import json
import cv2
import requests
import os
import tarfile
import io

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
    __ownIPFSUrl                    :str
    
    IV                              :bytearray
    ownIP                           :str
    nPort                           :int
    socketReceived                  :socket
    socketBroadcastSend             :socket
    web3                            :Web3

    def __init__(self, strNodeName, ownIP, addrEth, socketW3, strOwnIPFS):
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
        self.sendFrameBytes = 61440
        self.__ownIPFSUrl = 'http://' + strOwnIPFS

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

        # web3 connect
        self.web3 = Web3(Web3.HTTPProvider(f'http://{addrEth}:{socketW3}'))

    def __broadCastNodeData(self):
        dict_data = {self.__strNodeName : {"IP": self.ownIP, "Role": self.__strNodeRole, "PublicKey" : self.__pubKeyNode.to_string().hex()}}
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
            self.socketBroadcastSend.sendto(message, (self.broadCastIP, self.nPort))
            sleep(3)

        # 만약 누군가 끝났다고 Packet을 보내지 않았다면 아래를 수행.
        # 초기 노드들이 수집되었다면, 끝을 알리고, 다음을 진행.
        if not self.__eventSocket.is_set():
            typeSendE = struct.pack('c', b'E')
            self.socketBroadcastSend.sendto(typeSendE, (self.broadCastIP, self.nPort))
        
        # 자신이 가진 데이터를 모두 전송.
        # N||NodeList
        typeSendN = struct.pack('c', b'N')
        self.__dictReceivedData.update(dict_data)
        dataEncoded = json.dumps(self.__dictReceivedData).encode('utf-8')
        message = typeSendN + dataEncoded
        self.socketBroadcastSend.sendto(message, (self.broadCastIP, self.nPort))
        
    def __receivedNodeData(self):
        while True:
            self.__lockThread.acquire_lock()
            if self.__dictReceivedData.__len__() >= self.__nInitialNodeNumber:
                self.__lockThread.release_lock()
                break
            self.__lockThread.release_lock()
            
           # type, size check
            initialData, addr = self.socketReceived.recvfrom(61440)
            if addr[0] == self.ownIP:
                continue
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
            nodeListData, addr = self.socketReceived.recvfrom(61440)
            if addr[0] == self.ownIP:
                continue
            message_type = struct.unpack('c', nodeListData[:1])[0]
            if message_type == b'N':
                dictNodeData = json.loads(nodeListData[1:].decode('UTF-8'))
                oldDictSize = len(self.__dictReceivedData)
                self.__dictReceivedData.update(dictNodeData)
                print(f"업데이트 전 크기: {oldDictSize}, 업데이트 후 크기: {len(self.__dictReceivedData)}")
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
            pprint(self.__dictReceivedData, indent=4)
        except Exception as e:
            print(f"다음과 같은 오류가 발생했습니다.\n{e}")
            self.__listThread.clear()
            exit(1)
    
    def loadSecrete(self):
        with open('NodeKeyPair.json', 'r') as f:
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
    
    def getOwnIPFSAddr(self):
        return self.__ownIPFSUrl

    def setNodeRole(self, strNodeRole   :str):
        if strNodeRole == "Validator" or strNodeRole == "Sensor":
            self.__strNodeRole = strNodeRole
        else:
            raise Exception("올바르지 않는 Role을 부여했습니다")
        
    def setInitialNodeNumber(self, nNodeNum: int):
        self.__nInitialNodeNumber = nNodeNum
    
    def receivedSensorData(self, strNodeName):
        print(f"{strNodeName}의 Frame을 수신합니다.")

        nodeData = self.__dictReceivedData[strNodeName]
        if nodeData == None:
            raise Exception(f"{strNodeName}은 네트워크에 존재하지 않는 노드이름입니다.")            
        pubKeyNode=VerifyingKey.from_string(bytes.fromhex(nodeData['PublicKey']), curve=NIST256p)
        if pubKeyNode == None:
            raise Exception(f"{strNodeName}의 공개키가 존재하지 않습니다.")
        
        listFrameData = list()
        counter = 0
        totalFrames = self.sendFrameBytes
        try:
            while True:
                if counter == totalFrames:
                    break
                # S||timestamp||nFrameList||SID,SIG(F||AddrIPFS),AddrIPFS
                receivedData, addr = self.socketReceived.recvfrom(4096)
                if addr[0] == self.ownIP:
                    continue
                typePacket = struct.unpack('c', receivedData[:1])[0]
                if typePacket != b'S':
                    continue
                timestamp = struct.unpack('Q', receivedData[1:9])[0]
                totalFrames = struct.unpack('Q', receivedData[9:17])[0]
                splitingData = receivedData[17:].decode('UTF-8')
                splitedData = splitingData.split(',')

                if splitedData[0] != strNodeName:
                    continue

                signature = splitedData[1]
                addrIPFS = splitedData[2]
                frame = b''
                while True:
                    receivedFrame, addr = self.socketReceived.recvfrom(self.sendFrameBytes)
                    if addr[0] == self.ownIP:
                        continue
                    if receivedFrame == b'EndFrame':
                        break
                    frame = frame + receivedFrame
                
                message = f'{frame}{addrIPFS}'.encode("UTF-8")
                ret = pubKeyNode.verify(bytes.fromhex(signature), message, sha256)
                if not ret:
                    raise Exception(f"{pubKeyNode}의 {counter}번째 frame 검증에 실패했습니다.")
                
                listFrameData.append(frame)
                counter += 1
                
            self.__dictReceivedFrames[strNodeName] = listFrameData
            print(f"{strNodeName}의 총 {totalFrames} Frame을 저장하였습니다.")
            return timestamp, addrIPFS
            
        except Exception as e:
            print(f"{strNodeName}의 데이터를 수집하는 과정에서 아래 오류가 발생했습니다.\n{e}")
        
    def calculateMerkleTree(self, strNodeName):
        listRecedFrame = self.__dictReceivedFrames[strNodeName]
        listHashData = list()
        
        for frame in listRecedFrame:
            listHashData.append(sha256(frame).digest())
        
        while len(listHashData) != 1:
            if len(listHashData) % 2 != 0:
                listHashData.append(listHashData[-1])
                
            for i in range(len(listHashData)//2):
                left = listHashData.pop(0)
                right = listHashData.pop(0)
                listHashData.append(sha256(f'{left.hex()}{right.hex()}'.encode('UTF-8')).digest())
        
        return listHashData[0]

    def loadContractData(self):
        try:
            if not self.web3.is_connected():
                raise Exception("이더리움과 연결이 되어있지 않습니다.")
            
            # 계정 부여
            self.__accountNumer = ord(self.__strNodeName[4]) - ord('A') + 1
            self.web3.eth.default_account = self.web3.eth.accounts[self.__accountNumer]
            
            if not os.path.exists('SmartContract_Data.json'):
                print("SmartContract가 배포되어있지 않습니다.")
                exit(-1)
            
            with open('SmartContract_Data.json', 'r') as f:
                data = json.load(f)
                voteABI = data['Vote']['abi']
                voteAddr = data['Vote']['contractAddr']
                self.__contractVote = self.web3.eth.contract(
                    address=voteAddr,
                    abi=voteABI
                )
                searchABI = data['Search']['abi']
                searchAddr = data['Search']['contractAddr']
                self.__contractSearch = self.web3.eth.contract(
                    address=searchAddr,
                    abi=searchABI
                )

            print("모든 SmartContact가 Load되었습니다.")

            # 계정 등록
            self.__contractVote.functions.SignIn().transact()
            print("해당 SmartContract에 가입이 완료되었습니다.")
        except Exception as e:
            print(f'Error: {e}')
    
    def votingProcess(self, time, addrIPFS, strMerkleHash):
        try:
            # 특정 시간대 투표권한 얻기
            self.__contractVote.functions.GetVoteRight(time).transact()

            # 안건 올리기
            self.__contractVote.functions.Proposal(self.__accountNumer, time, addrIPFS, strMerkleHash).transact()
        except Exception as e:
            print(f"Error:{e}")
        
    def downloadandDecrypt(self, time, addrIPFS):
        url = self.__ownIPFSUrl +f'/api/v0/get?arg={addrIPFS}'
        path = os.getcwd()
        outputpath = str(path)+f'{self.__strNodeName}.text'
        response = requests.post(url)
        if response.status_code == 200:
            strNodeName = input("복호화할 영상의 주인을 입력해주세요.: ")
            with open('NodeKeyPair.json', 'r') as f:
                data = json.load(f)
                dictKeyPair = data[strNodeName]
                priv = list(dictKeyPair.keys())[0]
                pub = dictKeyPair[priv]
                bytesPub = bytes.fromhex(pub)

            token = input("Node로부터 전달받은 Token을 입력헤주세요.: ")
            bytetoken = bytes.fromhex(token)
            key = bytes(a ^ b for a, b in zip(bytesPub[:16], bytetoken[:16]))
            print(f"Calculated Key: {key.hex()}")

            cipher = AES.new(key, AES.MODE_CBC, self.IV)

            tar_data = io.BytesIO(response.content)
        
            # tar 파일로 열기
            with tarfile.open(fileobj=tar_data, mode='r:*') as tar:
                # 첫 번째 파일 멤버 가져오기
                member = tar.next()
                # 파일 데이터 추출
                file_data = tar.extractfile(member).read()
                print(f"Data Len: {len(file_data)}")
        else:
            print(f"Failed to download. Status code: {response.status_code}")
            return
        DecryptedData = cipher.decrypt(file_data)
        NonPaddedData = unpad(DecryptedData, AES.block_size)
        
        currentPath = os.getcwd()
        with open(currentPath+"/DecryptedData.avi", 'wb') as f:
            f.write(NonPaddedData) 


## Node Sensor & Verification
class NodeSV(NodeV):
    __strSensorURL          :str
    __dicttSensorData       :dict   #ex) [ "time": {"IPFSAddr": "addr", "Frames": []}, ....]
    __dictTimeKey           :dict   #ex) {"time":"Key"}

    def __init__(self, strNodeName  :str, ownIP, strURL, strOwnIPFS, addrEth, sockEth):
        super().__init__(strNodeName, ownIP, addrEth, sockEth, strOwnIPFS)
        self.__strSensorURL = strURL
        self.setNodeRole("Sensor")
        self.loadSecrete()
        self.__dicttSensorData = dict()
        self.__dictTimeKey = dict()
        
    def __generateToken(self, pubkey):
        nPubkey = len(pubkey)
        randomBytes = os.urandom(nPubkey)
        return randomBytes

    def __uploadSensorDataIPFS(self, fileName):
        url = self.getOwnIPFSAddr() +'/api/v0/add'
        
        pubkey = self.getOwnPublicKey().to_string()[:16]
        token = self.__generateToken(pubkey)[:16]
        key = bytes(a ^ b for a, b in zip(pubkey, token))
        print(f"Token(hex): {token.hex()}")
        print(f"Encryption Key: {key.hex()}")
        cipher = AES.new(key, AES.MODE_CBC, self.IV)

        with open(fileName, 'rb') as f:
            data = f.read()
        ciphertext = cipher.encrypt(pad(data, AES.block_size))
        file = {'file': ciphertext}
        # params = {'wrap-with-directory': 'true'}
        response = requests.post(url, files=file)
        if response.status_code == 200:
            self.__dictTimeKey[fileName] = token
            print("Upload IPFS Done")
            return json.loads(response.text)
        else:
            raise Exception("영상을 IPFS에 올리지 못했습니다.")
    
    def getSensorData(self, timeDelay):
        # Get Video Data
        timeCurrent =  int(datetime.timestamp(datetime.now()) * 1000)

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
            res = self.__uploadSensorDataIPFS(filePath)
            print(f"From IPFS\n{res}")
            
            IPFSDataHash = res['Hash']
            innerJson = {"IPFSAddr":IPFSDataHash, "Frames": videoFrame}
            
            # "time": {"IPFSAddr": "addr", "Frames": []}
            self.__dicttSensorData[timeCurrent] = innerJson
            return timeCurrent, IPFSDataHash
            
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
        packedTimeStamp = struct.pack('Q', timeSensor)
        strNodeName = self.getNodeName()
        
        # S||timestamp||nFrameList||SID,SIG(F||AddrIPFS),AddrIPFS,Frame
        # S||timestamp||nFrameList
        bcastmessage = packedType  + packedTimeStamp + packedLengthFrames
        
        priv = self.getOwnPrivateKey()
        for frame in listFrames:
            messageSign = f'{frame}{addrIPFS}'.encode("UTF-8")
            sig = priv.sign_deterministic(
                messageSign,
                hashfunc=sha256
            )
            
            # S||timestamp||nFrameList||SID,SIG(F||AddrIPFS),AddrIPFS
            sendMessage = bcastmessage + f'{strNodeName},{sig.hex()},{addrIPFS}'.encode('UTF-8')
            self.socketBroadcastSend.sendto(sendMessage, (self.broadCastIP, self.nPort))
            
            if len(frame) % self.sendFrameBytes != 0:
                sendCount = len(frame) // self.sendFrameBytes + 1
            else:
                sendCount = len(frame) // self.sendFrameBytes
                
            for i in range(sendCount):
                message = frame[i*self.sendFrameBytes:(i+1)*self.sendFrameBytes]
                self.socketBroadcastSend.sendto(message, (self.broadCastIP, self.nPort))
                sleep(0.01)
            self.socketBroadcastSend.sendto(b"EndFrame", (self.broadCastIP, self.nPort))
        print(f"Total {len(listFrames)} frame Send Done")

    def calculateSensingDataMerkleTree(self, time):
        collectionsSensorData = self.__dicttSensorData[time]
        listFrames = collectionsSensorData['Frames']
        listHashData = list()
        
        for frame in listFrames:
            listHashData.append(sha256(frame).digest())
        
        while len(listHashData) != 1:
            if len(listHashData) % 2 != 0:
                listHashData.append(listHashData[-1])
                
            for i in range(len(listHashData)//2):
                left = listHashData.pop(0)
                right = listHashData.pop(0)
                listHashData.append(sha256(f'{left.hex()}{right.hex()}'.encode('UTF-8')).digest())
        
        return listHashData[0]