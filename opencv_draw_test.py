import cv2
import os

# def drawCircle(event, x,y, flags, param):
#    img = param["img"]
#    now = time.monotonic()

#    def paint():
#       print("circle draw")
#       cv2.circle(img,(x,y), 10, (0,0,255), -1)

#    if event == cv2.EVENT_LBUTTONDOWN:
#       last_click = param.get("last_click")
#       if last_click and now - last_click[0] <= 0.4 and (x - last_click[1]) ** 2 + (y - last_click[2]) ** 2 <= 400:
#          paint()
#          param["last_click"] = None
#          param["last_draw"] = (now, x, y)
#       else:
#          param["last_click"] = (now, x, y)
#    elif event == cv2.EVENT_LBUTTONDBLCLK:
#       last_draw = param.get("last_draw")
#       if not (last_draw and now - last_draw[0] < 0.1 and (x - last_draw[1]) ** 2 + (y - last_draw[2]) ** 2 <= 400):
#          paint()
#       param["last_click"] = None
#       param["last_draw"] = (now, x, y)

      

def drawCircle(event, x,y, flags, param):
   img = param
   if event == cv2.EVENT_LBUTTONDBLCLK:
      print("circle draw")
      cv2.circle(img,(x,y), 10, (0,0,255), -1)

def doubleClickDrawing():
   root= os.getcwd()
   imgPath = os.path.join(root,'placeholder.jpg')
   img = cv2.imread(imgPath)
   
   name = "Demo Drawing App"
   cv2.namedWindow(name)
   cv2.setMouseCallback(name, drawCircle, img)
   
   
   while True:
      cv2.imshow(name, img)
      if cv2.waitKey(1) == ord('q'):
         break
   
class DrawingApp:
   def __init__(self, imagePath):
      self.imagePath = imagePath
      
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
         cv2.line(img, (self.startX, self.startY), (x,y), (255,255,255), 5)
         # update coordinates
         self.startX, self.startY = x,y
      elif event == cv2.EVENT_LBUTTONUP:
         print("Stop Drawing")
         self.isDrawing = False
         # cv2.circle(img,(x,y), 10, (0,0,255), -1)
         # cv2.line(img, (self.startX, self.startY), (x,y), (255,255,255), 5)
         
   def run(self):
      cap = cv2.VideoCapture(0)
      img = cv2.imread(self.imagePath)
      # img = cv2.imread(self.imagePath)
      
      name = "Demo Drawing App"
      cv2.namedWindow(name)
      
      while True:
         ret, frame = cap.read()
         cv2.setMouseCallback(name, self.drawLine, frame)
         cv2.imshow(name, frame)
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