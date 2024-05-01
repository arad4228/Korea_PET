import subprocess
import shlex

def convert_hls_to_mp4(hls_url, output_file, duration):
    command = f"ffmpeg -i {shlex.quote(hls_url)} -t {duration} -c copy {shlex.quote(output_file)}"
    try:
        # subprocess를 사용하여 타임아웃 설정
        process = subprocess.run(command, shell=True, timeout=duration+5, text=True, capture_output=True)
        if process.returncode == 0:
            print("변환 완료:", output_file)
        else:
            print("오류 발생:", process.stderr)
    except subprocess.TimeoutExpired:
        print("처리 시간 초과")


# 사용 예
hls_url = "http://210.179.218.52:1935/live/148.stream/playlist.m3u8"
output_file = "output.mp4"
duration = 20  # 추출할 영상의 길이(초)
convert_hls_to_mp4(hls_url, output_file, duration)
