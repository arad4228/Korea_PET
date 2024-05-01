from Node import *

if __name__ == "__main__":
    SensorA = NodeSV("NodeA", 8080,"http://210.179.218.52:1935/live/148.stream/playlist.m3u8")
    SensorA.getSensorData(10)