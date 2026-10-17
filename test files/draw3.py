import cv2
import os
import numpy as np

from cv2_gui import create_button_manager, create_toggle_button


# Portion of code from: https://github.com/krithika-pixel/Virtual-drawing-openCV/blob/main/live-webcam-drawing-sourcecode.txt

frameWidth = 640
frameHeight = 480


cap = cv2.VideoCapture(0)  
# cap.set(3, frameWidth)
# cap.set(4, frameHeight)
# cap.set(10, 150)  


myColors = [
    [5, 107, 0, 19, 255, 255],     # Orange
    [133, 56, 0, 159, 156, 255],   # Pink
    [57, 76, 0, 100, 255, 255],    # Green
    [90, 48, 0, 118, 255, 255]     # Blue
]



myColorValues = [
    [51, 153, 255],    # Orange
    [255, 0, 255],     # Pink
    [0, 255, 0],       # Green
    [255, 0, 0]        # Blue
]






class DrawingApp:
   def __init__(self, imagePath):
      self.myPoints = []
      self.imagePath = imagePath
      self.imgResult = None
      
      # global coordinates and drawing state
      self.startX, self.startY = 0, 0
      self.isDrawing = False

   def drawLine(self, event, x, y, flags, param):
      img = param
      if event == cv2.EVENT_LBUTTONDOWN:
         print("Start Drawing")
         # enable drawing flag
         self.isDrawing = True
         # update coordinates
         self.startX, self.startY = x,y
      elif event == cv2.EVENT_MOUSEMOVE and self.isDrawing:
         print("Now Drawing")
         # self.isDrawing = False
         # cv2.circle(img,(x,y), 10, (0,0,255), -1)
         self.myPoints.append([self.startX, self.startY, x, y])
         # cv2.line(img, (self.startX, self.startY), (x,y), (255,255,255), 5)
         # update coordinates
         self.startX, self.startY = x,y
      elif event == cv2.EVENT_LBUTTONUP:
         print("Stop Drawing")
         self.isDrawing = False
         # cv2.circle(img,(x,y), 10, (0,0,255), -1)
         # cv2.line(img, (self.startX, self.startY), (x,y), (255,255,255), 5)
         
   def drawOnCanvas(self):
      for point in self.myPoints:
         cv2.line(self.imgResult, (point[0], point[1]), (point[2],point[3]), (255,255,255), 5)
         # cv2.line(imgResult, (point[0], point[1]), 10, (255,255,255), 3)
         
   def run(self):
      cap = cv2.VideoCapture(0)
      img = cv2.imread(self.imagePath)
      # img = cv2.imread(self.imagePath)
      
      name = "Demo Drawing App"
      cv2.namedWindow(name)
      
      while True:
         ret, frame = cap.read()
         imgResult = frame.copy()
         self.imgResult = imgResult
         # print(imgResult)
         
         cv2.setMouseCallback(name, self.drawLine, self.imgResult)
         self.drawOnCanvas()
         cv2.imshow(name, imgResult)
         if cv2.waitKey(1) == ord('q'):
            break

def holdAndDragDrawing():
   root= os.getcwd()
   imgPath = os.path.join(root,'placeholder.jpg')
   app = DrawingApp(imgPath)
   app.run()


if __name__ == '__main__':
   # doubleClickDrawing()
   holdAndDragDrawing()