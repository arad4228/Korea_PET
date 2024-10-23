#!/bin/bash

# 필요한 인터페이스 수
NUM_INTERFACES=$1

if [ -z "$NUM_INTERFACES" ]; then
  echo "Usage: $0 <number-of-interfaces>"
  exit 1
fi

BRIDGE_NAME=br0

# 브리지 생성
ip link add name $BRIDGE_NAME type bridge
ip link set $BRIDGE_NAME up

# 가상 이더넷 인터페이스 생성 및 브리지에 연결
for i in $(seq 0 $(($NUM_INTERFACES-1)))
do
    # 단일 veth 인터페이스 생성
    ip tuntap add dev veth$i mode tap
    
    # IP 할당 및 활성화
    ip addr add 10.0.0.$(($i+1))/24 broadcast 10.255.255.255 dev veth$i
    ip link set veth$i up
    
    # veth 인터페이스를 브리지에 연결
    ip link set veth$i master $BRIDGE_NAME
    ip link set veth$i state UP
done

# 브리지에 IP 할당
ip addr add 10.0.0.254/24 broadcast 10.255.255.255 dev $BRIDGE_NAME

# 상태 확인
ip addr show $BRIDGE_NAME
for i in $(seq 0 $(($NUM_INTERFACES-1)))
do
    ip addr show veth$i
done

echo "가상 네트워크 설정 완료. 생성된 인터페이스끼리 통신 및 브로드캐스트가 가능합니다."
