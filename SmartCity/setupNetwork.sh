#!/bin/bash

# 필요한 네임스페이스 수
NUM_NAMESPACES=$1

if [ -z "$NUM_NAMESPACES" ]; then
  echo "Usage: $0 <number-of-namespaces>"
  exit 1
fi

# 브리지 생성
BRIDGE_NAME="br0"
ip link add name $BRIDGE_NAME type bridge
if [ $? -ne 0 ]; then
  echo "Failed to create bridge $BRIDGE_NAME"
  exit 1
fi
ip addr add 10.10.10.1/24 dev $BRIDGE_NAME
ip link set $BRIDGE_NAME up
if [ $? -ne 0 ]; then
  echo "Failed to set bridge $BRIDGE_NAME up"
  exit 1
fi

# IP 포워딩 및 브로드캐스트 설정
sysctl -w net.ipv4.ip_forward=1
echo 0 > /proc/sys/net/bridge/bridge-nf-call-iptables
echo 0 > /proc/sys/net/bridge/bridge-nf-call-ip6tables

# 네임스페이스 생성 및 설정
for i in $(seq 1 $NUM_NAMESPACES); do
  NS="ns$i"
  VETH_HOST="veth_host$i"
  VETH_NS="veth_ns$i"
  IP_NS="10.10.10.$((i+1))"

  # 네임스페이스 생성
  ip netns add $NS
  if [ $? -ne 0 ]; then
    echo "Failed to create namespace $NS"
    continue
  fi

  # veth 쌍 생성
  ip link add $VETH_HOST type veth peer name $VETH_NS
  if [ $? -ne 0 ]; then
    echo "Failed to create veth pair $VETH_HOST and $VETH_NS"
    ip netns del $NS
    continue
  fi

  # veth 인터페이스를 네임스페이스에 연결
  ip link set $VETH_NS netns $NS
  if [ $? -ne 0 ]; then
    echo "Failed to set $VETH_NS to namespace $NS"
    ip link del $VETH_HOST
    ip netns del $NS
    continue
  fi

  # 네임스페이스 내부 인터페이스 설정
  ip netns exec $NS ip addr add $IP_NS/24 dev $VETH_NS
  ip netns exec $NS ip link set $VETH_NS up
  ip netns exec $NS ip route add default via 10.10.10.1

  # 호스트 측 인터페이스 설정
  ip addr add 10.10.10.$((100 + i))/24 dev $VETH_HOST
  ip link set $VETH_HOST up

  # 브리지에 인터페이스 연결
  ip link set $VETH_HOST master $BRIDGE_NAME

  # 네임스페이스 내에서 브로드캐스트 주소 설정
  ip netns exec $NS ip route add broadcast 10.10.10.255 dev $VETH_NS
done

# 브로드캐스트 및 P2P 통신을 위한 iptables 설정 (필요 시 추가)
iptables -A FORWARD -i $BRIDGE_NAME -o $BRIDGE_NAME -j ACCEPT

echo "Virtual network setup complete."
