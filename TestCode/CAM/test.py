import cv2
import site

print(print(site.getsitepackages()))


capture = cv2.VideoCapture(0)
capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

while cv2.waitKey(33) < 0:
    ret, frame = capture.read()
    frame = cv2.flip(frame,1)
    cv2.imshow("VideoFrame", frame)


capture.release()
cv2.destroyAllWindows()