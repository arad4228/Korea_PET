from Node import *

if __name__ == "__main__":
    pubSensorA = '503be5f47066ae161edf1cc74a18e1088bdc8a9d06f953ee992ead02e1da46c6ed0fa6b95a6b8040d6bed0e572425d0705209510b84fba4c89998078cd0aee8b'
    SensorA = NodeSV(pubSensorA, 8080,"http://210.179.218.52:1935/live/148.stream/playlist.m3u8")
    SensorA.getSensorData(10)