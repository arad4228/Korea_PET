from ecdsa import SigningKey, VerifyingKey, NIST256p
from collections import OrderedDict
from web3 import Web3
from solcx import install_solc, compile_source
import json

class KGC:
    __pubkeyKGC             :VerifyingKey
    __privkeyKGC            :SigningKey
    __web3                  :Web3
    __accountKGC            :Web3.eth.default_account
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
            while priv not in listPrivKeys:
                priv = SigningKey.generate(curve=NIST256p)
            pub = priv.verifying_key
            listPrivKeys.append(priv)
            listPubkeys.append(pub)
        
        dictNdoeList = OrderedDict()
        for strNodeName in listNodeName:
            dictKeyPair = dict()
            dictKeyPair[priv] = pub
            dictNdoeList[strNodeName] = dictKeyPair
        
        with open("NodeKeyPair.json", 'w') as f:
            json.dump(dictNdoeList, f)
    
    def loadSmartContract(self, fileName):
        with open(fileName, 'w') as f:
            self.__strsmartContract = f.read()
                
    def deploySmartContact(self, addressEth, socketW3, versionSolc):
        try:
            self.__web3 = Web3(Web3.HTTPProvider(f'{addressEth}:{socketW3}'))
            if not self.__web3.is_connected():
                raise Exception("ETH에 접근할 수 없습니다. 아래와 같은 IP주소와 Port번호를 입력해주세요. \nex)address: http://127.0.0.1 port: 7545")
            
            # KGC의 계정은 0번
            self.__accountKGC = self.__web3.eth.accounts[0]
            
            install_solc(version=f'{versionSolc}')
            compileSol = compile_source(f'{self.__strsmartContract}', output_values=['abi', 'bin'], solc_version=versionSolc)
            contractId, contractInterface = compileSol.popitem()
            bytecode = contractInterface['bin']
            abi = contractInterface['abi']

            self.__smartContract = self.__web3.eth.contract(abi=abi, bytecode=bytecode)
            # Contract 배포
            receiptTX  = self.__smartContract.constructor().transact()
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