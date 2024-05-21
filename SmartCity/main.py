from Node import *
# from KGC import *
import sys

if __name__ == "__main__":
    # nodeList = ["NodeA", "NodeB", "NodeC", "NodeD"]
    # kgc = KGC()
    # kgc.generatePrivPubkey(nodeList, len(nodeList))
    
    # if sys.argc >= 4:
    #     print("프로그램을 실행하기 위한 인자가 부족합니다.")
    #     print("python3 main.py <NodeName> <NodeIP> <SecreteFileName> <Camera URL> <IPFS URL>")
    
    # strNodeName = sys.argv[1]
    # strIP = sys.argv[2]
    # file = sys.argv[3]
    
    strNodeName = 'NodeA'
    strIP = '10.0.0.1'
    file = 'NodeKeyPair.json'

    node = NodeSV(strNodeName, strIP, file, 'http://210.179.218.52:1935/live/148.stream/playlist.m3u8', 'aaa')
    # node.loadSecrete(file)
    # node.loadSecrete(file)
    print(node.getOwnPrivateKey().to_string().hex())
    # node = NodeSV(strNodeName, strIP, file, 'http://210.179.218.52:1935/live/147.stream/playlist.m3u8', 'aaa')
    # node.setInitialNodeNumber(4)
    # node.networkInitialize()
    time=node.getSensorData(10)
    node.sendSensorData(time)
    
    #node.receivedSensorData(strNodeName)