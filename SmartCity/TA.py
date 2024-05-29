from ecdsa import SigningKey, VerifyingKey, NIST256p
from collections import OrderedDict
from web3 import Web3
from solcx import install_solc, set_solc_version, compile_source
from pprint import pprint
import json
import os

class TA:
    __addressEth            :str
    __pubkeyTA              :VerifyingKey
    __privkeyTA             :SigningKey
    __web3                  :Web3
    __strsmartContract      :str
    
    def __init__(self, addressEth, socketW3,):
        self.__privkeyTA = SigningKey.generate(curve=NIST256p)
        self.__pubkeyTA = self.__privkeyTA.verifying_key

        self.__addressEth = addressEth
        self.__web3 = Web3(Web3.HTTPProvider(f'{addressEth}:{socketW3}'))
        if not self.__web3.is_connected():
            print("ETH에 접근할 수 없습니다. 아래와 같은 IP주소와 Port번호를 입력해주세요. \nex)address: http://127.0.0.1 port: 7545")
            exit(-1)
            
        # TA의 계정은 0번
        self.__web3.eth.default_account = self.__web3.eth.accounts[0]
        self.__strsmartContract = None
       
    
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
                
    def deploySmartContact(self, versionSolc):
        try:
            if self.__strsmartContract == None:
                raise Exception("배포하고자하는 SmartContract에 대해 로딩이 필요합니다.")
            
            version = install_solc(versionSolc)
            print(f'Solc version: {version}')
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

            contractData = OrderedDict()
            for contract_id, contract_interface in compileSol.items():
                if 'Vote' in contract_id or 'Search' in contract_id:
                    smartContract = self.__web3.eth.contract(abi=contract_interface['abi'], bytecode=contract_interface['bin']) 
                    contractTxHash  = smartContract.constructor().transact()
                    contractTxReceipt = self.__web3.eth.wait_for_transaction_receipt(contractTxHash)
                    print(f"{self.__addressEth}의 ETH에 다음과 같은 Smart Contract가 배포되었습니다.\n{contract_id}:{contractTxReceipt.contractAddress}")
                    
                    innerDict = dict()
                    innerDict['abi'] = contract_interface['abi']
                    innerDict['byteCode'] = contract_interface['bin']
                    innerDict['contractAddr'] = contractTxReceipt.contractAddress
                    if 'Vote' in contract_id:
                        contractData['Vote'] = innerDict

                        self.__contractVote = self.__web3.eth.contract(
                            address=contractTxReceipt.contractAddress,
                            abi=contract_interface['abi']
                        )

                        # erc-20 mint call
                        self.__contractVote.functions.erc20mint().call()
                        print("Vote Contract에 ERC-20이 발행되었습니다.")
                    else:
                        contractData['Search'] = innerDict

            with open('SmartContract_Data.json', 'w') as f:
                json.dump(contractData, f)
                
        except Exception as e:
            print(e)
    
    def printEthBlockInfo(self):
        pprint(dict(self.__web3.eth.get_block('latest')), indent=4)

    def printAllAcountInfo(self):
        accounts = self.__web3.eth.accounts
        for account in accounts:
            balance = self.__web3.eth.get_balance(account)
            print(f'{account}: {balance}')