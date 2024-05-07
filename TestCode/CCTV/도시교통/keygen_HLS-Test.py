import av
from ecdsa import SigningKey, VerifyingKey, NIST256p
from hashlib import sha256
import io
from time import time

url = "http://210.179.218.52:1935/live/148.stream/playlist.m3u8"
frame_list = []

def image_to_bytes(image):
    # BytesIO 객체 생성
    img_byte_arr = io.BytesIO()

    # 이미지를 BytesIO 객체에 저장 (예: PNG 형식으로)
    image.save(img_byte_arr, format='PNG')

    # BytesIO 객체를 바이트 데이터로 변환
    img_byte_arr = img_byte_arr.getvalue()

    return img_byte_arr

def receiver_job():
    print('Run Receiver Thread')
    container = av.open(url)

    video_stream = next(s for s in container.streams if s.type == 'video')
    start = time()
    for frame in container.decode(video_stream):
        if time() - start >= 2.0:
            break
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
    receiver_job()
    priv = SigningKey.generate(curve=NIST256p)
    print(f"Priv: {priv.to_string().hex()}")
    pub1 = priv.verifying_key
    print(f"Pubkey: {pub1.to_string().hex()}")
    bytes_pub = bytes.fromhex(pub1.to_string().hex())
    pub2 = VerifyingKey.from_string(bytes_pub, curve=NIST256p)
    if pub1 == pub2:
        print("same")
    else:
        print("diff")
    message = frame_list.pop(0).to_image()
    message = image_to_bytes(message)
    start = time()
    sig = priv.sign_deterministic(
        message,
        hashfunc=sha256
    )
    try:
        ret = pub1.verify(sig, message, sha256)
        assert ret
        print(f"diff: {time()-start}")
        print("True")
    except:
        print("fail")