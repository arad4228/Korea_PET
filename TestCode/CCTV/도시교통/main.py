from multiprocessing import Process, Manager
from threading import Thread
import time
import av

url = "http://210.179.218.52:1935/live/148.stream/playlist.m3u8"
frame_list = []

def receiver_job():
    print('Run Receiver Thread')
    container = av.open(url)

    video_stream = next(s for s in container.streams if s.type == 'video')

    for frame in container.decode(video_stream):
        frame_list.append(frame)

def makePNG_job():
    print('Run makePNG Thread')
    i = 0
    while True:
        if len(frame_list) == 0:
            time.sleep(1)
            continue
        frame = frame_list.pop(0)
        frame.to_image().save(f'{i}.png')
        i +=1


if __name__ == "__main__":
    thread_list = []
    thread_list.append(Thread(target=receiver_job))
    thread_list.append(Thread(target=makePNG_job))
    
    for thread in thread_list:
        thread.start()