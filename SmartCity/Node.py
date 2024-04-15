from socket import *
import threading
import time
import hashlib
import av

MAX_Size = 10000

class NodeV:
    __strNodeName           :str
    __strNodeRole           :str
    __pairKeys              :list
    __listNodes             :list
    __nInitialNodeNumber    :int
    __dictReceivedData      :dict  # key: strNode, value: strIP
    __lockThread            :threading.Lock
    __listThread            :list
    __listFrames            :dict
    
    def __init__(self, strName  :str, strRole='Validator'):
        self.__strNodeName = strName
        self.__strNodeRole = strRole
        self.__lockThread = threading.Lock()
    
    def setInitialNodeNumber(self, nNodeNum: int):
        self.__nInitialNodeNumber = nNodeNum

    def getOwnSecrete(self):
        return self.__pairkeys
    
    def broadCastNodeData(self):
        # Lock을 얻고 몇개의 데이터를 가지고 있는지 리스트를 확인
        self.__lockThread.aquire()
        if len(self.__listNodes) >= self.__nInitialNodeNumber:
            self.__lockThread.release()
            return True
        
        self.__lockThread.release()
        ## 모든 네트워크 대역에 Broadcast

    def receivedNodeData(self):
        ## 패킷을 전달받고.
        
        ## 전달받는 로직(ToBe)

        newNode = list()
        self.__lockThread.acquire()
        self.__listNodes.append(newNode)
        self.__lockThread.release()

    def sendListNodeData(self):
        # BroadCast Node List data;
        # length of Node | list data
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
        for frame in listFrame:
            # ToBe continue