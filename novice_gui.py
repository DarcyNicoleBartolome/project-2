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

import json

class Drawing(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.myPoints = []
        self.imgResult = None
        self.drawingColor = "#202020"
        self.pen_size = 5
        self.eraser_mode = False
        
        self.strokes = []
        self.json_file = "stroke.json"
        self.last_json_data = None
        
        # the window name, e.g "notepad", "Chrome", etc.
        self.window_name = "Blender"
        self.windows = gw.getWindowsWithTitle(self.window_name)
        if not self.windows:
            raise RuntimeError(f"No window found with title containing {self.window_name!r}")

        self.width = pyautogui.size().width
        self.height = pyautogui.size().height

        self.hwnd = self.windows[0]._hWnd
        self.capture_width, self.capture_height = win32gui.GetClientRect(self.hwnd)[2:]
        
        
        # global coordinates and drawing state
        self.startX, self.startY = 0, 0
        self.isDrawing = False
        
        # Set the Window information
        self.title("Project 2 - Novice")
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
        
        self.canvas = Canvas(self.preview, highlightthickness=0,
                                    cursor="crosshair")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.last_point = None
        self.stroke_items = []
        
        # Create the background image item once, then update it each frame.
        self.video_item = self.canvas.create_image((0,0), image="", anchor=NW)
        
        # Camera state
        self._stop = threading.Event()
        self._latest_frame_rgb = None
        self._frame_lock = threading.Lock()
        self._latest_imgtk = None
        self._capture_interval = 1 / 30
        
        # with Image.open("test.png") as im:
        self.x1 = self.canvas.winfo_rootx() + self.canvas.winfo_x()
        self.y1 = self.canvas.winfo_rooty() + self.canvas.winfo_y()
        self.x2 = self.x1 + self.canvas.winfo_width()
        self.y2 = self.y1 + self.canvas.winfo_height()

        threading.Thread(
            target=self._reader_loop,
            daemon=True
        ).start()

        self.after(33, self._render_latest_frame)
        
        self.after(100, self.load_strokes)


    def _reader_loop(self):
        while not self._stop.is_set():
            started = time.perf_counter()
            try:
                frame = self.background_screenshot(
                    self.hwnd, self.capture_width, self.capture_height
                )
                # BitBlt creates a BGRA buffer, not a BGR one.
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)

                # Overlay a pointer marker because background window captures
                # commonly omit the Windows cursor.
                cursor_x, cursor_y = pyautogui.position()
                left, top, _, _ = win32gui.GetWindowRect(self.hwnd)
                cursor_x -= left
                cursor_y -= top
                if 0 <= cursor_x < frame_rgb.shape[1] and 0 <= cursor_y < frame_rgb.shape[0]:
                    cv2.circle(frame_rgb, (cursor_x, cursor_y), 9, (255, 255, 255), 2)
                    cv2.circle(frame_rgb, (cursor_x, cursor_y), 3, (255, 40, 40), -1)

                with self._frame_lock:
                    self._latest_frame_rgb = frame_rgb
            except Exception as exc:
                print(f"Screen capture failed: {exc}")

            # Keep capture cadence near 30 FPS without consuming a CPU core.
            remaining = self._capture_interval - (time.perf_counter() - started)
            if remaining > 0:
                self._stop.wait(remaining)


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
            # self.drawOnCanvas()
            
            # Convert NumPy frame to a Pillow image
            pil_image = Image.fromarray(self.imgResult)

            # Resize to fit the preview
            width = max(self.canvas.winfo_width(), 1)
            height = max(self.canvas.winfo_height(), 1)

            pil_image.thumbnail((width, height), Image.Resampling.BILINEAR)

            # Create PhotoImage version
            self._latest_imgtk = ImageTk.PhotoImage(pil_image)
            x = max((self.canvas.winfo_width() - self._latest_imgtk.width()) // 2, 0)
            y = max((self.canvas.winfo_height() - self._latest_imgtk.height()) // 2, 0)
            self.canvas.coords(self.video_item, x, y)
            self.canvas.itemconfigure(self.video_item, image=self._latest_imgtk)
            self.canvas.tag_lower(self.video_item)
            # pil_image.save("canvas_result.jpg")

        self.after(33, self._render_latest_frame)
        
    def background_screenshot(self, hwnd, width, height):
        wDC = win32gui.GetWindowDC(hwnd)
        dcObj=win32ui.CreateDCFromHandle(wDC)
        cDC=dcObj.CreateCompatibleDC()
        dataBitMap = win32ui.CreateBitmap()
        dataBitMap.CreateCompatibleBitmap(dcObj, width, height)
        cDC.SelectObject(dataBitMap)
        cDC.BitBlt((0,0),(width, height) , dcObj, (0,0), win32con.SRCCOPY)
        image = np.frombuffer(dataBitMap.GetBitmapBits(True), dtype=np.uint8).reshape(height, width, 4)
        dcObj.DeleteDC()
        cDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, wDC)
        win32gui.DeleteObject(dataBitMap.GetHandle())
        return image
    
    def load_strokes(self):
        if not self.winfo_exists():
            return

        try:
            with open(self.json_file, "r") as f:
                strokes = json.load(f)

            # Only redraw when the JSON data changes.
            if strokes != self.last_json_data:
                self.last_json_data = strokes

                self.canvas.delete("annotation")

                for stroke in strokes:
                    self.canvas.create_line(
                        stroke["x1"],
                        stroke["y1"],
                        stroke["x2"],
                        stroke["y2"],
                        fill=stroke["color"],
                        width=stroke["width"],
                        capstyle=ROUND,
                        joinstyle=ROUND,
                        smooth=True,
                        tags="annotation"
                    )

                self.canvas.tag_lower(self.video_item)

        except (FileNotFoundError, json.JSONDecodeError):
            pass

        self.after(100, self.load_strokes)
        
# Starting the client
def start_screen():
   # Start GUI
   app = Drawing()
   app.mainloop()
      
if __name__ == "__main__":
   start_screen()