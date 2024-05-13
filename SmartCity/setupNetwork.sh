#!/bin/bash

# 인자로 전달된 숫자 확인
if [ -z "$1" ]; then
  echo "사용법: $0 <생성할 인터페이스 개수>"
  exit 1
fi

NUM_INTERFACES=$1

# iproute2 설치
apt-get update
apt-get install -y iproute2

# 더미 인터페이스 생성 루프
for ((i=0; i<NUM_INTERFACES; i++))
do
  INTERFACE_NAME="dummy${i}"
  IP_ADDRESS="192.168.1.$((i+1))/24"
  
  echo "생성 중: $INTERFACE_NAME, IP 주소: $IP_ADDRESS"
  
  ip link add $INTERFACE_NAME type dummy
  ip addr add $IP_ADDRESS dev $INTERFACE_NAME
  ip link set $INTERFACE_NAME up
done

echo "모든 인터페이스 생성 완료."
