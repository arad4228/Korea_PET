from threading import Thread, Event, Lock
from time import *
import socket
import datetime
import hashlib
import av
import subprocess
import shlex

MAX_Size = 10000

## Verification Node
class NodeV:
    __strNodeName           :str
    __strNodeRole           :str
    __pairKeys              :list
    __listNodes             :dict
    __nInitialNodeNumber    :int
    __dictReceivedData      :dict  # key: strNodeRole, value: strIP
    __lockThread            :Lock
    __listThread            :list
    __listFrames            :dict

    __socketSendFrame       :socket
    __socketReceived        :socket
    
    def __init__(self, strName, port):
        self.__strNodeName = strName
        self.__strNodeRole = 'Validator'
        self.__lockThread = Lock()
        # 받고 보낼 소켓 생성
        self.__socketSendFrame = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__socketReceived = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 보내는 소켓은 BroadCast, 받는 소캣은 전부 수용하도록 설정
        self.__socketSendFrame.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.__socketReceived.bind(('', port))

    def getNodeName(self):
        return self.__strNodeName
    
    def setNodeRole(self, strNodeRole   :str):
        self.__strNodeRole = strNodeRole
        
    def setInitialNodeNumber(self, nNodeNum: int):
        self.__nInitialNodeNumber = nNodeNum

    def getOwnSecrete(self):
        return self.__pairkeys
    
    def broadCastNodeData(self, port):
        while True:
            # Lock을 얻고 몇개의 데이터를 가지고 있는지 리스트를 확인
            self.__lockThread.aquire()
            if len(self.__listNodes) >= self.__nInitialNodeNumber:
                self.__lockThread.release()
                break
            self.__lockThread.release()

            ## 모든 네트워크 대역에 Broadcast
            message = (self.__strNodeName + self.__strNodeRole).encode("UTF-8")
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

    def receivedSensorData(self, strNodeName):
        # 전달 받고 T까지 전달 받음.
        listFrameData = list

        while True:
            # received packet
            # if packet 이 end라면 stop
            # data 받아서 list 추가
            data = 'data'    # 수정
            listFrameData.append(data)
        
        self.__listFrames[strNodeName] = listFrameData
        
    def calculateMerkle(self, strNodeName):
        listFrame = self.__listFrames[strNodeName]
        listHashFrame = list
        # for frame in listFrame:
            # ToBe continue


## Node Sensor & Verification
class NodeSV(NodeV):
    __strSensorURL          :str
    __listSensorFrame       :list
    __event                 :Event

    def __init__(self, strName  :str, port, strURL    :str):
        super().__init__(strName, port)
        self.__strSensorURL = strURL
        self.setNodeRole("Sensor")
        self.__event = Event()
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