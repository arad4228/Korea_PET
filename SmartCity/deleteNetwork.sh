#!/bin/bash

# 필요한 인터페이스 수
NUM_INTERFACES=$1

if [ -z "$NUM_INTERFACES" ]; then
  echo "Usage: $0 <number-of-interfaces>"
  exit 1
fi

BRIDGE_NAME=br0

# 가상 이더넷 인터페이스 제거
for i in $(seq 0 $(($NUM_INTERFACES-1)))
do
    ip link del veth$i
done

# 브리지 제거
ip link del $BRIDGE_NAME 2>/dev/null

echo "가상 네트워크 설정이 제거되었습니다."
