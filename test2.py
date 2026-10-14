from tkinter import *
from tkinter import ttk
import customtkinter as ctk
# from PIL import Image, ImageTk
import threading
import os
import cv2
import numpy as np

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


class Drawing(ctk.CTk):
   def __init__(self):
      super().__init__()
      
      # Set the Window information
      self.title("Project 2")
      self.geometry("1000x650")
      self.minsize(850, 560)
      
      # Layout
      self.grid_rowconfigure(0, weight=1)
      self.grid_rowconfigure(1, weight=0)
      self.grid_columnconfigure(0, weight=0)
      self.grid_columnconfigure(1, weight=1)
      self.grid_columnconfigure(2, weight=0)

      # Left
      self.left = ctk.CTkFrame(self, corner_radius=16)
      self.left.grid(row=0, column=0, padx=(18, 10), pady=(18, 10), sticky="ns")
      
      button = ctk.CTkButton(self.left, text="Clear canvas", command=self.clear_canvas)
      button.grid(row=1, column=0, padx=12, pady=0)
      
      # Screen
      self.center = ctk.CTkFrame(self, corner_radius=18)
      self.center.grid(row=0, column=1, padx=10, pady=(18, 10), sticky="nsew")
      self.center.grid_rowconfigure(0, weight=1)
      self.center.grid_columnconfigure(0, weight=1)

      self.preview = ctk.CTkFrame(self.center, corner_radius=18)
      self.preview.grid(row=0, column=0, padx=14, pady=14, sticky="nsew")
      self.preview.grid_rowconfigure(0, weight=1)
      self.preview.grid_columnconfigure(0, weight=1)

      self.canvas = Canvas(self.preview, background="white", highlightthickness=0,
                           cursor="crosshair")
      self.canvas.grid(row=0, column=0, sticky="nsew")
      self.canvas.bind("<Button-1>", self.start_stroke)
      self.canvas.bind("<B1-Motion>", self.draw_stroke)
      self.canvas.bind("<ButtonRelease-1>", self.end_stroke)
      self.last_point = None

   def start_stroke(self, event):
      self.last_point = (event.x, event.y)

   def draw_stroke(self, event):
      if self.last_point is None:
         return
      x, y = event.x, event.y
      self.canvas.create_line(
         self.last_point[0], self.last_point[1], x, y,
         fill="#202020", width=5, capstyle=ROUND, joinstyle=ROUND,
         smooth=True
      )
      self.last_point = (x, y)

   def end_stroke(self, event):
      self.last_point = None

   def clear_canvas(self):
      self.canvas.delete("all")

def button_event():
   print("button pressed")


# Starting the client
def start_screen():
   # Start GUI
   app = Drawing()
   app.mainloop()
      
if __name__ == "__main__":
   start_screen()