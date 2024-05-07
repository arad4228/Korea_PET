import cv2

# HLS 스트림 URL
hls_stream_url = "http://210.179.218.52:1935/live/148.stream/playlist.m3u8"

# HLS 스트림 열기
cap = cv2.VideoCapture(hls_stream_url)

# 비디오 속성 가져오기
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = 50

# VideoWriter 객체 생성
fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter('output.avi', fourcc, fps, (width, height))

# 스트림이 정상적으로 열렸는지 확인
if not cap.isOpened():
    print("스트림을 열 수 없습니다.")
    exit()

# 30초 동안 프레임을 읽고 저장
start_time = cv2.getTickCount() / cv2.getTickFrequency()
while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 프레임 저장
    out.write(frame)

    # 프레임 처리 (예시: 화면에 표시)
    cv2.imshow('HLS Stream', frame)

    # 30초가 지나면 종료
    current_time = cv2.getTickCount() / cv2.getTickFrequency()
    if current_time - start_time >= 30:
        break

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 영상 재생 종료 후, 리소스 해제
cap.release()
out.release()
cv2.destroyAllWindows()
