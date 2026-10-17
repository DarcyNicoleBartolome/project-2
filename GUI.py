from tkinter import *
import customtkinter as ctk
from PIL import Image, ImageTk
import threading
import os
import cv2
import numpy as np
import time

import pyautogui
import win32gui
import win32ui
import win32con

import pygetwindow as gw

from CTkColorPicker import *


class Drawing(ctk.CTk):
   def __init__(self):
      super().__init__()
      
      self.myPoints = []
      self.imgResult = None
      self.drawingColor = "#202020"

      # the window name, e.g "notepad", "Chrome", etc.
      self.window_name = "Blender"
      
      # global coordinates and drawing state
      self.startX, self.startY = 0, 0
      self.isDrawing = False
      
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
      
      button = ctk.CTkButton(self.left, text="Clear Canvas", command=self.clear_canvas)
      button.grid(row=1, column=0, padx=12, pady=9)
      
      self.colorbutton = ctk.CTkButton(self.left, text="CHOOSE COLOR", text_color="black", command=self.ask_color)
      self.colorbutton.grid(row=2, column=0, padx=12, pady=6)
      
      # Screen / preview
      self.center = ctk.CTkFrame(self, corner_radius=18)
      self.center.grid(
         row=0, column=1,
         padx=10, pady=(18, 10),
         sticky="nsew"
      )

      self.center.grid_rowconfigure(0, weight=1)
      self.center.grid_columnconfigure(0, weight=1)

      self.preview = ctk.CTkFrame(self.center, corner_radius=18)
      self.preview.grid(
         row=0, column=0,
         padx=14, pady=14,
         sticky="nsew"
      )

      self.preview.grid_rowconfigure(0, weight=1)
      self.preview.grid_columnconfigure(0, weight=1)
      
      self.canvas = Canvas(self.preview, highlightthickness=0, cursor="crosshair")
      self.canvas.grid(row=0, column=0, sticky="nsew")
      self.canvas.bind("<Button-1>", self.start_stroke)
      self.canvas.bind("<B1-Motion>", self.draw_stroke)
      self.canvas.bind("<ButtonRelease-1>", self.end_stroke)
      self.last_point = None
      
      self.video_text = self.canvas.create_text((50,50), text = "Starting camera")
      
      # Create the background image item once, then update it each frame.
      self.video_item = self.canvas.create_image((0, 0), image="", anchor=NW)
      

      # Camera state
      self._stop = threading.Event()
      self._latest_frame_rgb = None
      self._frame_lock = threading.Lock()
      self._latest_imgtk = None

      # Open camera
      self.cap = cv2.VideoCapture(0)

      if not self.cap.isOpened():
         # pass
         self.canvas.itemconfigure(self.video_text, text="Cannot open camera")
      else:
         self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
         self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

         threading.Thread(
            target=self._reader_loop,
            daemon=True
         ).start()

         self.after(33, self._render_latest_frame)


   def _reader_loop(self):
      while not self._stop.is_set():
         if self.cap is None or not self.cap.isOpened():
               break

         ok, frame = self.cap.read()

         if not ok:
               time.sleep(0.05)
               continue

         # Convert OpenCV BGR to RGB
         frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

         with self._frame_lock:
               self._latest_frame_rgb = frame_rgb


   def _render_latest_frame(self):
      if self._stop.is_set():
         return

      with self._frame_lock:
         frame = (
               self._latest_frame_rgb.copy()
               if self._latest_frame_rgb is not None
               else None
         )

      if frame is not None:
         imgResult = frame.copy()
         self.imgResult = imgResult
         self.drawOnCanvas()
         
         # Convert NumPy frame to a Pillow image
         pil_image = Image.fromarray(self.imgResult)

         # Resize to fit the preview
         width = max(self.canvas.winfo_width(), 1)
         height = max(self.canvas.winfo_height(), 1)

         pil_image.thumbnail((width, height))
         
         # Create PhotoImage version
         self._latest_imgtk = ImageTk.PhotoImage(pil_image)
         
         self.canvas.itemconfigure(self.video_item, image=self._latest_imgtk)

      self.after(33, self._render_latest_frame)


   def start_stroke(self, event):
         self.last_point = (event.x, event.y)
   
   def draw_stroke(self, event):
      if self.last_point is None:
         return
      x, y = event.x, event.y
      self.canvas.create_line(
         self.last_point[0], self.last_point[1], x, y,
         fill=self.drawingColor, width=5, capstyle=ROUND, joinstyle=ROUND,
         smooth=True,
         tags="line"
      )
      self.last_point = (x, y)

   def end_stroke(self, event):
      self.last_point = None

   def clear_canvas(self):
      self.canvas.delete("line")
      
   def ask_color(self):
      pick_color = AskColor() # open the color picker
      color = pick_color.get() # get the color string
      self.colorbutton.configure(fg_color=color)
      self.drawingColor = color

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

   def on_close(self):
      self._stop.set()

      if self.cap is not None:
         self.cap.release()
         self.cap = None

      self.destroy()

   def background_screenshot(self, hwnd, width, height):
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
      
def button_event():
   print("button pressed - Clear Drawing")
   


# Starting the client
def start_screen():
   # Start GUI
   app = Drawing()
   app.mainloop()
      
if __name__ == "__main__":
   start_screen()