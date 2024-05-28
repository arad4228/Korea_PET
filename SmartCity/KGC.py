from ecdsa import SigningKey, VerifyingKey, NIST256p
from collections import OrderedDict
from web3 import Web3
from solcx import install_solc, set_solc_version, compile_source
import json
import os

class KGC:
    __pubkeyKGC             :VerifyingKey
    __privkeyKGC            :SigningKey
    __web3                  :Web3
    __strsmartContract      :str
    
    def __init__(self):
        self.__privkeyKGC = SigningKey.generate(curve=NIST256p)
        self.__pubkeyKGC = self.__privkeyKGC.verifying_key
    
    def generatePrivPubkey(self, listNodeName, nClient):
        # "ID" : {"Priv": "Pub"}
        listPrivKeys = []
        listPubkeys = []
        for i in range(nClient):
            priv = SigningKey.generate(curve=NIST256p)
            while True:
                if priv not in listPrivKeys:
                    break
                priv = SigningKey.generate(curve=NIST256p)
            pub = priv.verifying_key
            listPrivKeys.append(priv.to_string().hex())
            listPubkeys.append(pub.to_string().hex())
        
        dictNdoeList = OrderedDict()
        for strNodeName, hexPirv, hexPub in zip(listNodeName, listPrivKeys, listPubkeys):
            dictKeyPair = dict()
            dictKeyPair[hexPirv] = hexPub
            dictNdoeList[strNodeName] = dictKeyPair
        
        with open("NodeKeyPair.json", 'w') as f:
            json.dump(dictNdoeList, f)
    
    def loadSmartContract(self, fileName):
        with open(fileName, 'r') as f:
            self.__strsmartContract = f.read()
                
    def deploySmartContact(self, addressEth, socketW3, versionSolc):
        try:
            self.__web3 = Web3(Web3.HTTPProvider(f'{addressEth}:{socketW3}'))
            if not self.__web3.is_connected():
                raise Exception("ETH에 접근할 수 없습니다. 아래와 같은 IP주소와 Port번호를 입력해주세요. \nex)address: http://127.0.0.1 port: 7545")
            
            # KGC의 계정은 0번
            self.__accountKGC = self.__web3.eth.accounts[0]
            
            install_solc(versionSolc)
            set_solc_version(versionSolc)
            node_modules_path = os.path.join(os.getcwd(), "node_modules")

            compileSol = compile_source(
                f'{self.__strsmartContract}', 
                output_values=['abi', 'bin'], 
                allow_paths=[node_modules_path],
                solc_version=versionSolc,
                import_remappings=[
                    f"hardhat={os.path.join(node_modules_path, 'hardhat')}",
                    f"@openzeppelin={os.path.join(node_modules_path, '@openzeppelin')}"
                ]                
            )

            contractId, contractInterface = compileSol.popitem()
            bytecode = contractInterface['bin']
            abi = contractInterface['abi']

            self.__smartContract = self.__web3.eth.contract(abi=abi, bytecode=bytecode)
            # Contract 배포
            receiptTX  = self.__smartContract.constructor().transact() #error!!!
            print(f"{addressEth}의 ETH에 다음과 같은 Smart Contract가 배포되었습니다.\n{receiptTX}")
            
            contractData = OrderedDict()
            contractData['abi'] = abi
            contractData['bytecode'] = bytecode
            jsonContractData = dict()
            jsonContractData[receiptTX] = contractData
            with open('SmartContract_Data.json', 'w') as f:
                json.dump(jsonContractData, f)
                
        except Exception as e:
            print(e)