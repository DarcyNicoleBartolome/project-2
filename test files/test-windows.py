# import cv2
# import numpy as np
# import pyautogui
# import pygetwindow as gw
# import sys


# # the window name, e.g "notepad", "Chrome", etc.
# window_name = "Blender"

# # print(gw.getAllWindows())
# # print(gw.getAllTitles())
# w = gw.getWindowsWithTitle(window_name)


# # define the codec
# fourcc = cv2.VideoWriter_fourcc(*"XVID")
# # frames per second
# fps = 60.0
# # the time you want to record in seconds
# record_seconds = 10

# # search for the window, getting the first matched window with the title
# w = gw.getWindowsWithTitle(window_name)[0]
# # activate the window
# w.activate()


# # search for the window, getting the first matched window with the title
# w = gw.getWindowsWithTitle(window_name)[0]
# # activate the window
# w.activate()

# # create the video write object
# out = cv2.VideoWriter("output.avi", fourcc, fps, tuple(w.size))

# for i in range(int(record_seconds * fps)):
#     # make a screenshot
#     img = pyautogui.screenshot(region=(w.left, w.top, w.width, w.height))
#     # convert these pixels to a proper numpy array to work with OpenCV
#     frame = np.array(img)
#     # convert colors from BGR to RGB
#     frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
#     # write the frame
#     out.write(frame)
#     # show the frame
#     # cv2.imshow("screenshot", frame)
#     # if the user clicks q, it exits
#     if cv2.waitKey(1) == ord("q"):
#         break

# # make sure everything is closed when exited
# cv2.destroyAllWindows()
# out.release()


# Source - https://stackoverflow.com/a/62293957
# Posted by Alexandre Calil
# Retrieved 2026-10-15, License - CC BY-SA 4.0

import pyautogui
import win32gui
import win32ui
import win32con

import pygetwindow as gw
import numpy as np
import cv2


# the window name, e.g "notepad", "Chrome", etc.
window_name = "Blender"

print(gw.getAllWindows())
print(gw.getAllTitles())
w = gw.getWindowsWithTitle(window_name)
print(w)
w = gw.getWindowsWithTitle(window_name)[0]
print(w)

def background_screenshot(hwnd, width, height):
    wDC = win32gui.GetWindowDC(hwnd)
    dcObj=win32ui.CreateDCFromHandle(wDC)
    cDC=dcObj.CreateCompatibleDC()
    dataBitMap = win32ui.CreateBitmap()
    dataBitMap.CreateCompatibleBitmap(dcObj, width, height)
    cDC.SelectObject(dataBitMap)
    cDC.BitBlt((0,0),(width, height) , dcObj, (0,0), win32con.SRCCOPY)
    dataBitMap.SaveBitmapFile(cDC, 'screenshot.bmp')
    
    image =  np.frombuffer(dataBitMap.GetBitmapBits(True), dtype=np.uint8).reshape(height, width, 4)
    dcObj.DeleteDC()
    cDC.DeleteDC()
    win32gui.ReleaseDC(hwnd, wDC)
    win32gui.DeleteObject(dataBitMap.GetHandle())
    return image



windows = gw.getWindowsWithTitle(window_name)
if not windows:
    raise RuntimeError(f"No window found with title containing {window_name!r}")

width = pyautogui.size().width
height = pyautogui.size().height

hwnd = windows[0]._hWnd
print(win32gui.IsWindowVisible(hwnd))

while True:
    frame = background_screenshot(hwnd, width, height)
    # GDI returns BGRA pixels; OpenCV's display expects BGR.
    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    cv2.imshow("Blender livestream", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cv2.destroyAllWindows()


