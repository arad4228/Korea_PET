# 구동용 추가 라이브러리
1. sudo apt install python-opencv

# 필요한 라이브러리 설치(Docker용)
1. ./starting.sh

# 이더리움 동작시키기
ganache -h 0.0.0.0 -p 8545 -v -a 100 --db ./EthData/ChainDB/ --logging.file ./EthData/log/logfile.log