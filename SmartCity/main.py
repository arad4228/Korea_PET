from Node import *
# from KGC import *
import sys

if __name__ == "__main__":
    # nodeList = ["NodeA", "NodeB", "NodeC", "NodeD"]
    # kgc = KGC()
    # kgc.generatePrivPubkey(nodeList, len(nodeList))
    
    if sys.argc >= 4:
        print("프로그램을 실행하기 위한 인자가 부족합니다.")
        print("python3 main.py <NodeName> <NodeIP> <SecreteFileName> <Camera URL> <IPFS URL>")
    
    strNodeName = sys.argv[1]
    strIP = sys.argv[2]
    file = sys.argv[3]
    
    # strNodeName = 'NodeA'
    # strIP = '10.0.0.1'
    # file = 'Desktop/Korea_PET/SmartCity/NodeKeyPair.json'
    
    node = NodeSV(strNodeName, strIP, file, 'aaa', 'aaa')
    node.setInitialNodeNumber(4)
    node.networkInitialize()