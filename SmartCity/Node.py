from socket import *
import threading
import hashlib
import av

MAX_Size = 10000

class NodeV:
    __strNodeName           :str
    __strNodeRole           :str
    __pairKeys              :list
    __listNodes             :dict
    __nInitialNodeNumber    :int
    __dictReceivedData      :dict  # key: strNodeRole, value: strIP
    __lockThread            :threading.Lock
    __listThread            :list
    __listFrames            :dict

    __socketSendFrame       :socket
    __socketReceived        :socket
    
    def __init__(self, strName  :str, port):
        self.__strNodeName = strName
        self.__strNodeRole = 'Validator'
        self.__lockThread = threading.Lock()
        # 받고 보낼 소켓 생성
        self.__socketSendFrame = socket(AF_INET, SOCK_DGRAM)
        self.__socketReceived = socket(AF_INET, SOCK_DGRAM)
        # 보내는 소켓은 BroadCast, 받는 소캣은 전부 수용하도록 설정
        self.__socketSendFrame.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.__socketReceived.bind(('', port))

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


class NodeSV(NodeV):
    __strSensorURL          :str
    __listSensorFrame       :list

    def __init__(self, strName  :str, strURL    :str):
        super.__init__(strName, "Sensor")
        self.__strSensorURL = strURL

    def getSensorData(self):
        container = av.open(self.strURL)
        video_stream = next(s for s in container.streams if s.type == 'video')
        for frame in container.decode(video_stream):
            self.__listSensorFrame.append(frame)

    def snedSensorData(self):
        print("f")      # 수정