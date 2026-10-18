from tkinter import filedialog
from tkinter import *
import customtkinter as ctk
from PIL import Image, ImageTk, ImageGrab, ImageChops
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
        self.stroke_data = []


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
        self.title("Project 2 - Expert")
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
        
        self.clear_button = ctk.CTkButton(self.left, text="Clear Canvas", command=self.clear_canvas)
        self.clear_button.grid(row=1, column=0, padx=12, pady=9)
        
        self.paint_button = ctk.CTkButton(self.left, text="Paint", command=self.toggle_eraser_mode)
        self.paint_button.grid(row=3, column=0, padx=12, pady=9)
        
        self.colorbutton = ctk.CTkButton(self.left, text="CHOOSE COLOR", text_color="black", command=self.ask_color)
        self.colorbutton.grid(row=4, column=0, padx=12, pady=6)
        
        self.text = ctk.CTkLabel(self.left, text="Pen Size", corner_radius=0)
        self.text.grid(row=5, column=0, padx=12, pady=2)      
        self.pen_size_slider = ctk.CTkSlider(self.left, from_=1, to=50, command=self.set_pen_size)
        self.pen_size_slider.grid(row=6, column=0, padx=12, pady=2)
        self.pen_size_slider.set(self.pen_size)
        
        self.avatar_button = ctk.CTkButton(self.left, text="Avatar", text_color="black", command=self.handle_avatar)
        self.avatar_button.grid(row=7, column=0, padx=12, pady=36)
        self.marker_button = ctk.CTkButton(self.left, text="Marker", text_color="black", command=self.add_marker)
        self.marker_button.grid(row=8, column=0, padx=12, pady=6)
        
        self.text2 = ctk.CTkLabel(self.left, text="Chatbox", corner_radius=0)
        self.text2.grid(row=9, column=0, padx=12, pady=2)     
        self.chatbox = ctk.CTkTextbox(self.left)
        # self.chatbox.insert("0.0", "end")
        self.chatbox.grid(row=10, column=0, padx=2, pady=2)
        self.sendchatbutton = ctk.CTkButton(self.left, text="Send", text_color="black", command=self.send_message)
        self.sendchatbutton.grid(row=11, column=0, padx=12, pady=6)

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
        self.canvas.bind("<Button-1>", self.start_stroke)
        self.canvas.bind("<B1-Motion>", self.draw_stroke)
        self.canvas.bind("<ButtonRelease-1>", self.end_stroke)
        self.last_point = None
        self.stroke_items = []
        self._canvas_save_after_id = None
        
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

        self.after(33, self._render_latest_frame)


    def start_stroke(self, event):
        self.last_point = (event.x, event.y)
    
    def draw_stroke(self, event):
        if self.eraser_mode:
            x1, y1 = event.x-self.pen_size/2, event.y-self.pen_size/2
            x2, y2 = event.x+self.pen_size/2, event.y+self.pen_size/2
            # find all items under cursor
            items = self.canvas.find_overlapping(x1, y1, x2, y2)
            # erase items except the background image
            for item in items:
                if item in self.stroke_items:
                    self.canvas.delete(item)
                    self.stroke_items.remove(item)

                    self.stroke_data = [
                        stroke for stroke in self.stroke_data if stroke["item"] != item
                    ]

                    
        elif self.last_point is None:
            return
        else:
            x, y = event.x, event.y
            item = self.canvas.create_line(
                self.last_point[0], self.last_point[1], x, y,
                fill=self.drawingColor, width=self.pen_size, capstyle=ROUND, joinstyle=ROUND,
                smooth=True,
                tags="line"
            )
            self.stroke_items.append(item)
            self.stroke_data.append({
                "type": "stroke",
                "item": item,
                "x1": self.last_point[0],
                "y1": self.last_point[1],
                "x2": event.x,
                "y2": event.y,
                "color": self.drawingColor,
                "width": self.pen_size,
            })
            self.last_point = (x, y)
            
        with open('stroke.json', 'w') as f:
            json.dump(self.stroke_data, f)

    def end_stroke(self, event):
        self.last_point = None
    
    def toggle_eraser_mode(self):
        self.eraser_mode = not self.eraser_mode
        if self.eraser_mode:
            self.paint_button.configure(text="Erase")
        else:
            self.paint_button.configure(text="Paint")

    def clear_canvas(self):
        for item in self.stroke_items:
            self.canvas.delete(item)
            
        self.stroke_items.clear()
        self.stroke_data.clear()
        with open('stroke.json', 'w') as f:
            json.dump(self.stroke_data, f)
    def on_close(self):
        self._stop.set()

        self.destroy()
        
    def ask_color(self):
        pick_color = AskColor() # open the color picker
        color = pick_color.get() # get the color string
        self.colorbutton.configure(fg_color=color)
        self.drawingColor = color

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
    
    
    
    def set_pen_size(self, value):
        self.pen_size = value
   
    def handle_avatar(self):
        print("handle avatar")
        
    def add_marker(self):
        print("add marker from avatar")
        
    def send_message(self):
        pass


# Starting the client
def start_screen():
   # Start GUI
   app = Drawing()
   app.mainloop()
      
if __name__ == "__main__":
   start_screen()