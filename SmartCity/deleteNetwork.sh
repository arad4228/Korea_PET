#!/bin/bash

# 인자로 전달된 숫자 확인
if [ -z "$1" ]; then
  echo "사용법: $0 <제거할 인터페이스 개수>"
  exit 1
fi

NUM_INTERFACES=$1

# 더미 인터페이스 제거 루프
for ((i=0; i<NUM_INTERFACES; i++))
do
  INTERFACE_NAME="dummy${i}"
  
  echo "제거 중: $INTERFACE_NAME"
  
  ip link delete $INTERFACE_NAME
done

echo "모든 인터페이스 제거 완료."