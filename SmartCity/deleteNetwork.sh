#!/bin/bash

# 필요한 네임스페이스 수
NUM_NAMESPACES=$1

if [ -z "$NUM_NAMESPACES" ]; then
  echo "Usage: $0 <number-of-namespaces>"
  exit 1
fi

# 네임스페이스와 veth 인터페이스 삭제
for i in $(seq 1 $NUM_NAMESPACES); do
  NS="ns$i"
  VETH_HOST="veth_host$i"

  # 네임스페이스 삭제
  ip netns del $NS
  if [ $? -ne 0 ]; then
    echo "Failed to delete namespace $NS"
  fi

  # 호스트 측 veth 인터페이스 삭제
  ip link del $VETH_HOST
  if [ $? -ne 0 ]; then
    echo "Failed to delete veth interface $VETH_HOST"
  fi
done

# 브리지 삭제
BRIDGE_NAME="br0"
ip link set $BRIDGE_NAME down
ip link del $BRIDGE_NAME

echo "Virtual network teardown complete."
