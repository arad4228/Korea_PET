#!/bin/bash

apt-get update
apt install -y build-essential curl wget tar git libglib2.0-0 libgl1 iproute2 net-tools iputils-ping 
apt install -y python3 python3-pip tshark nodejs npm

# 필요한 SmartContract자료 다운로드
npm install --save-dev hardhat
npm install @openzeppelin/contracts
npm install ganache --global