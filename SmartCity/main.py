from Node import *
from TA import *
import sys

if __name__ == "__main__":

    if sys.argv[1] == 'TA':
        ta = TA(f'http://{sys.argv[2]}', 8545)
        # ta.getEthBlockInfo()
        
        # TA로부터 keypair 발급
        nodeList = ["NodeA", "NodeB", "NodeC", "NodeD", "NodeE"]
        ta.generatePrivPubkey(nodeList)
        
        # TA가 SmartContract 배퐆
        ta.loadSmartContract('contract.sol')
        ta.deploySmartContact('0.8.20')
        
        while True:
            time = int(input("시간을 입력하세요: "))
            ta.endOfVoting(time)

    elif 'Node' in sys.argv[1]:
        if len(sys.argv) <= 4:
            print("프로그램을 실행하기 위한 인자가 부족합니다.")
            print("python3 main.py <NodeName> <NodeIP> <Camera URL> <IPFS URL> <EthAddr> <Eth Port>")
            exit(-1)
        
        strNodeName = sys.argv[1]
        strIP = sys.argv[2]
        cameraURL = sys.argv[3] # http://210.179.218.52:1935/live/148.stream/playlist.m3u8
        IPFSAddr = sys.argv[4]
        addrEth = sys.argv[5]
        socktEth = sys.argv[6]
        
        node = NodeSV(strNodeName, strIP, cameraURL, IPFSAddr, addrEth, socktEth)
        nNode = int(input("초기 네트워크 설정인원을 입력해주세요: "))
        node.setInitialNodeNumber(nNode)
        node.networkInitialize()
        
        if strNodeName == "NodeA":
            timeDelay = int(input("몇초의 영상을 저장하고 싶은지 입력하세요: "))
            time, receivedAddrIPFS = node.getSensorData(timeDelay)
            node.sendSensorData(time)
            strMerkleValue = node.calculateSensingDataMerkleTree(time)
            print(f'Calculate Merkle Hash value:{strMerkleValue.hex()}')
        else:
            time, receivedAddrIPFS = node.receivedSensorData('NodeA')
            strMerkleValue = node.calculateMerkleTree('NodeA')
            print(f"Calculate Merkle Hash value:{strMerkleValue.hex()}")

        node.loadContractData()
        node.votingProcess(time, receivedAddrIPFS, strMerkleValue)
        print(f"time: {time}\nIPFS: {receivedAddrIPFS}\nMerkleRoot: {strMerkleValue.hex()}\n로 투표를 진행했습니다.")

        if strNodeName != "NodeA":
            check = input("Sensor Data 복호화 여부: ")
            if check == "Y" or check == "y":
                node.downloadandDecrypt(time, receivedAddrIPFS)
                print("복호화가 완료되었습니다.")
    else:
        print("프로그렘을 실행할 충분한 인자가 없습니다.")
        print("ex)python3 main.py TA")
        print("ex)python3 main.py Node(X) <NodeIP> <SecreteFileName> <Camera URL> <IPFS URL>")