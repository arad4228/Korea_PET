from Node import *
# from KGC import *
import sys

if __name__ == "__main__":
    # nodeList = ["NodeA", "NodeB", "NodeC", "NodeD", "NodeE"]
    # kgc = KGC()
    # kgc.generatePrivPubkey(nodeList, len(nodeList))
    
    if len(sys.argv) <= 4:
        print("프로그램을 실행하기 위한 인자가 부족합니다.")
        print("python3 main.py <NodeName> <NodeIP> <SecreteFileName> <Camera URL> <IPFS URL>")
        exit(-1)
    
    strNodeName = sys.argv[1]
    strIP = sys.argv[2]
    file = sys.argv[3]
    cameraURL = sys.argv[4] # http://210.179.218.52:1935/live/148.stream/playlist.m3u8
    IPFSAddr = sys.argv[5]
    
    node = NodeSV(strNodeName, strIP, file, cameraURL, IPFSAddr)
    nNode = int(input("초기 네트워크 설정인원을 입력해주세요: "))
    node.setInitialNodeNumber(nNode)
    node.networkInitialize()
    
    if strNodeName == "NodeA":
        time = node.getSensorData(10)
        print(time)
        node.sendSensorData(time)
    else:
        node.receivedSensorData('NodeA') 
        print(f"Calculate Merkle Tree:{node.calculateMerkleTree('NodeA')}")