# code used by both the expert and novice GUIs: finding and capturing blender,
# the canvas that shows it, the chat box, sounds and icons.
import json
import os
import tempfile
import threading
import time
from datetime import datetime
from tkinter import Canvas, NW, ROUND, HIDDEN, NORMAL

import customtkinter as ctk
import cv2
import numpy as np
import pyautogui
import win32con
import win32gui
import win32ui
from PIL import Image, ImageChops, ImageOps, ImageTk


# folder this file is in (the project folder).
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# the GUIs talk to each other through small json files in windows' temp folder.
SHARED_DIR = os.path.join(tempfile.gettempdir(), "cpsc581_project2")
os.makedirs(SHARED_DIR, exist_ok=True)

STROKE_FILE = os.path.join(SHARED_DIR, "stroke.json")
CHAT_FILE = os.path.join(SHARED_DIR, "chat.json")
# expert -> blender: "place blendy / a flag where I clicked" (read by blender_listener.py).
COMMAND_FILE = os.path.join(SHARED_DIR, "blender_commands.json")
# blender -> both GUIs: what happened last, plus a heartbeat showing blender is listening.
BLENDER_STATUS_FILE = os.path.join(SHARED_DIR, "blender_status.json")

SOUND_DIR = os.path.join(PROJECT_DIR, "sounds")
ICON_DIR = os.path.join(PROJECT_DIR, "icons")


# loads a black icon from the icons folder and makes it white so it shows up on the buttons.
# returns None if the file isn't there (the button then just shows its text).
def load_icon(filename, size=(18, 18)):
    path = os.path.join(ICON_DIR, filename)
    if not os.path.exists(path):
        return None
    image = Image.open(path).convert("RGBA")
    # dark pixels are the icon shape (works with a transparent or a white background).
    alpha = ImageChops.multiply(image.getchannel("A"), ImageOps.invert(image.convert("L")))
    white_icon = Image.new("RGBA", image.size, (255, 255, 255, 0))
    white_icon.putalpha(alpha)
    return ctk.CTkImage(light_image=white_icon, dark_image=white_icon, size=size)


# plays sounds/<name>.wav without waiting for it to finish (windows only).
def play_sound(name):
    path = os.path.join(SOUND_DIR, f"{name}.wav")
    if not os.path.exists(path):
        return
    try:
        import winsound
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception as exc:  # no sound device, not on windows, etc.
        print(f"Could not play {name}.wav: {exc}")


# loads a json file, or returns default if it's missing or can't be read.
def read_json(path, default):
    for attempt in range(10):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except PermissionError:
            # the other GUI is swapping in a new version right now, so try again.
            time.sleep(0.01)
        except (OSError, ValueError):
            return default
    return default


# what blender_listener.py last reported, and whether it's still running.
# returns (status or None, connected). the listener updates "heartbeat" at least every 2 seconds.
def read_blender_status():
    status = read_json(BLENDER_STATUS_FILE, None)
    if not isinstance(status, dict):
        return None, False
    return status, time.time() - status.get("heartbeat", 0) < 6


# saves data as json. writes to a temporary file first and then swaps it in,
# so the other GUI never reads a half-written file.
def write_json(path, data):
    tmp_path = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        for attempt in range(10):
            try:
                os.replace(tmp_path, path)
                return
            except PermissionError:
                # on windows the swap fails while the other GUI is reading the file.
                # it only holds it for a few milliseconds, so try again.
                time.sleep(0.01)
        print(f"Could not update {os.path.basename(path)} (file busy)")
    except OSError as exc:
        print(f"Could not write {os.path.basename(path)}: {exc}")
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


# every blender window on windows uses this window class (set in blender's source code,
# intern/ghost/intern/GHOST_SystemWin32.cc), so we never grab a chrome tab or
# vs code file that just has "Blender" in its title.
BLENDER_WINDOW_CLASS = "GHOST_WindowClass"


# finds blender's main window (returns None if blender isn't open).
def find_blender_window():
    found = []

    def check(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetClassName(hwnd) == BLENDER_WINDOW_CLASS:
            found.append(hwnd)
        return True

    win32gui.EnumWindows(check, None)
    if not found:
        return None

    # blender can have extra windows open (e.g. preferences), so pick the biggest one.
    # GetWindowPlacement gives the normal size even if the window is minimized.
    def normal_area(hwnd):
        left, top, right, bottom = win32gui.GetWindowPlacement(hwnd)[4]
        return (right - left) * (bottom - top)

    return max(found, key=normal_area)


# takes a picture of the inside of a window (without the title bar and borders).
# returns (picture, (x, y) of its top-left corner on screen), or (None, None) if the window has no size.
def grab_window(hwnd):
    width, height = win32gui.GetClientRect(hwnd)[2:]
    if width <= 0 or height <= 0:
        return None, None

    # where the inside of the window starts: on screen, and within the whole window.
    client_x, client_y = win32gui.ClientToScreen(hwnd, (0, 0))
    window_left, window_top = win32gui.GetWindowRect(hwnd)[:2]
    offset = (client_x - window_left, client_y - window_top)

    wDC = win32gui.GetWindowDC(hwnd)
    dcObj = win32ui.CreateDCFromHandle(wDC)
    cDC = dcObj.CreateCompatibleDC()
    dataBitMap = win32ui.CreateBitmap()
    try:
        dataBitMap.CreateCompatibleBitmap(dcObj, width, height)
        cDC.SelectObject(dataBitMap)
        cDC.BitBlt((0, 0), (width, height), dcObj, offset, win32con.SRCCOPY)
        image = np.frombuffer(dataBitMap.GetBitmapBits(True), dtype=np.uint8).reshape(height, width, 4)
    finally:
        dcObj.DeleteDC()
        cDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, wDC)
        win32gui.DeleteObject(dataBitMap.GetHandle())

    # BitBlt creates a BGRA buffer, not an RGB one.
    return cv2.cvtColor(image, cv2.COLOR_BGRA2RGB), (client_x, client_y)


# grabs pictures of the blender window about 30 times a second on a background thread.
# keeps working if blender isn't open yet, or gets minimized, resized, closed and reopened.
# status = message to show the user when something's wrong ("" = everything is fine).
class BlenderCapture:
    def __init__(self, fps=30):
        self.interval = 1 / fps
        self.hwnd = None
        self.status = "Looking for Blender..."
        self._latest_frame = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        threading.Thread(target=self._loop, daemon=True).start()

    # the most recent picture of blender (None = no picture yet).
    def latest_frame(self):
        with self._lock:
            return self._latest_frame

    def stop(self):
        self._stop.set()

    def _loop(self):
        while not self._stop.is_set():
            started = time.perf_counter()
            try:
                self._grab_once()
            except Exception as exc:
                # e.g. blender closed halfway through a capture, so look for it again.
                print(f"Screen capture failed: {exc}")
                self.hwnd = None

            # keeps capture near 30 fps without using a whole cpu core.
            remaining = self.interval - (time.perf_counter() - started)
            if remaining > 0:
                self._stop.wait(remaining)

    def _grab_once(self):
        if self.hwnd is None or not win32gui.IsWindow(self.hwnd):
            self.hwnd = find_blender_window()
            if self.hwnd is None:
                self.status = "Open Blender to start sharing"
                with self._lock:
                    self._latest_frame = None
                self._stop.wait(1)  # no need to look more than once a second
                return

        if win32gui.IsIconic(self.hwnd):
            # minimized: keep showing the last picture until it's restored.
            self.status = "Blender is minimized - restore it to keep sharing"
            return

        frame, (left, top) = grab_window(self.hwnd)
        if frame is None:
            return

        # draws the mouse pointer, because window captures usually leave it out.
        cursor_x, cursor_y = pyautogui.position()
        cursor_x -= left
        cursor_y -= top
        if 0 <= cursor_x < frame.shape[1] and 0 <= cursor_y < frame.shape[0]:
            cv2.circle(frame, (cursor_x, cursor_y), 9, (255, 255, 255), 2)
            cv2.circle(frame, (cursor_x, cursor_y), 3, (255, 40, 40), -1)

        self.status = ""
        with self._lock:
            self._latest_frame = frame


# canvas that shows the live blender picture, centred and scaled to fit.
# drawings are saved as positions on the blender picture (0 to 1, e.g. x = 0.5 is the middle)
# instead of canvas pixels, so they land on the same spot in both GUIs whatever their size.
class BlenderCanvas(Canvas):
    def __init__(self, master, capture, on_picture_moved=None, **kwargs):
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("bg", "gray14")
        super().__init__(master, **kwargs)
        self.capture = capture
        # called whenever the picture moves or changes size, so drawings can be redrawn.
        self.on_picture_moved = on_picture_moved
        # where the blender picture is on the canvas: (x, y, width, height).
        self.picture_rect = None

        self._photo = None
        self._shown_frame = None
        self._shown_size = None
        self.video_item = self.create_image((0, 0), image="", anchor=NW)
        self.status_bg = self.create_rectangle(0, 0, 0, 0, fill="#202020", outline="", state=HIDDEN)
        self.status_item = self.create_text(0, 0, text="", fill="#f2f2f2", font=("Segoe UI", 13, "bold"))

        # short pop-up message at the bottom of the picture (see show_toast).
        self.toast_bg = self.create_rectangle(0, 0, 0, 0, fill="#202020", outline="#ffb454", width=2, state=HIDDEN)
        self.toast_item = self.create_text(0, 0, text="", fill="#ffffff", font=("Segoe UI", 13, "bold"), state=HIDDEN)
        self._toast_after_id = None

        self.after(33, self._render)

    # shows a short message at the bottom of the picture for a few seconds.
    def show_toast(self, text, seconds=3.5, color="#ffb454"):
        self.itemconfigure(self.toast_item, text=text, state=NORMAL)
        self.itemconfigure(self.toast_bg, outline=color, state=NORMAL)
        self._place_toast()
        if self._toast_after_id is not None:
            self.after_cancel(self._toast_after_id)
        self._toast_after_id = self.after(int(seconds * 1000), self._hide_toast)

    def _hide_toast(self):
        self._toast_after_id = None
        self.itemconfigure(self.toast_item, state=HIDDEN)
        self.itemconfigure(self.toast_bg, state=HIDDEN)

    def _place_toast(self):
        width, height = max(self.winfo_width(), 1), max(self.winfo_height(), 1)
        bottom = height - 30
        if self.picture_rect is not None:
            bottom = min(bottom, self.picture_rect[1] + self.picture_rect[3] - 30)
        self.coords(self.toast_item, width / 2, bottom)
        left, top, right, bottom = self.bbox(self.toast_item)
        self.coords(self.toast_bg, left - 14, top - 7, right + 14, bottom + 7)
        self.tag_raise(self.toast_bg)
        self.tag_raise(self.toast_item)

    # canvas pixel -> position on the blender picture (0 to 1).
    def to_picture(self, x, y):
        px, py, width, height = self.picture_rect
        return (x - px) / width, (y - py) / height

    # position on the blender picture (0 to 1) -> canvas pixel.
    def to_canvas(self, u, v):
        px, py, width, height = self.picture_rect
        return px + u * width, py + v * height

    # draws one saved line segment and returns its canvas item.
    def draw_segment(self, stroke, tags):
        x1, y1 = self.to_canvas(stroke["x1"], stroke["y1"])
        x2, y2 = self.to_canvas(stroke["x2"], stroke["y2"])
        # thickness is also saved as a fraction of the picture width.
        width = max(1, stroke["width"] * self.picture_rect[2])
        return self.create_line(
            x1, y1, x2, y2,
            fill=stroke["color"], width=width,
            capstyle=ROUND, joinstyle=ROUND, smooth=True,
            tags=tags,
        )

    def _render(self):
        frame = self.capture.latest_frame()
        size = (max(self.winfo_width(), 1), max(self.winfo_height(), 1))

        if frame is not None and (frame is not self._shown_frame or size != self._shown_size):
            self._shown_frame, self._shown_size = frame, size

            # converts the numpy frame to a pillow image, shrunk to fit the canvas.
            picture = Image.fromarray(frame)
            picture.thumbnail(size, Image.Resampling.BILINEAR)
            self._photo = ImageTk.PhotoImage(picture)

            x = max((size[0] - self._photo.width()) // 2, 0)
            y = max((size[1] - self._photo.height()) // 2, 0)
            self.coords(self.video_item, x, y)
            self.itemconfigure(self.video_item, image=self._photo)
            self.tag_lower(self.video_item)

            rect = (x, y, self._photo.width(), self._photo.height())
            if rect != self.picture_rect:
                self.picture_rect = rect
                if self.on_picture_moved:
                    self.on_picture_moved()

        elif frame is None and self._shown_frame is not None:
            # blender was closed, so stop showing the old picture.
            self._shown_frame = None
            self.itemconfigure(self.video_item, image="")

        self._show_status(self.capture.status, size, centred=self._shown_frame is None)
        if self._toast_after_id is not None:
            self._place_toast()  # keeps it on top of new drawings, and centred if resized
        self.after(33, self._render)

    # shows a message like "Open Blender to start sharing" on the canvas.
    def _show_status(self, text, size, centred):
        if not text:
            self.itemconfigure(self.status_item, state=HIDDEN)
            self.itemconfigure(self.status_bg, state=HIDDEN)
            return
        y = size[1] / 2 if centred else 28
        self.itemconfigure(self.status_item, text=text, state=NORMAL)
        self.coords(self.status_item, size[0] / 2, y)
        left, top, right, bottom = self.bbox(self.status_item)
        self.coords(self.status_bg, left - 12, top - 6, right + 12, bottom + 6)
        self.itemconfigure(self.status_bg, state=NORMAL)
        self.tag_raise(self.status_bg)
        self.tag_raise(self.status_item)


# chat between the expert and the novice, shared through chat.json.
class ChatPanel(ctk.CTkFrame):
    NAME_COLORS = {"Expert": "#6cb6ff", "Novice": "#ffb454"}

    def __init__(self, master, me, other, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.me = me
        self._shown_messages = None

        self.title_label = ctk.CTkLabel(self, text=f"Chat with {other}")
        self.title_label.grid(row=0, column=0, pady=(0, 2))

        self.log = ctk.CTkTextbox(self, width=200, height=150, wrap="word")
        self.log.grid(row=1, column=0, pady=2)
        for name, color in self.NAME_COLORS.items():
            self.log.tag_config(name, foreground=color)
        self.log.configure(state="disabled")  # read-only, messages are typed in the box below

        self.entry = ctk.CTkEntry(self, width=200, placeholder_text="Type a message...")
        self.entry.grid(row=2, column=0, pady=(4, 2))
        self.entry.bind("<Return>", lambda event: self.send())

        self.send_button = ctk.CTkButton(self, text="Send", image=load_icon("send.png"), command=self.send)
        self.send_button.grid(row=3, column=0, pady=(4, 0))

        self.after(300, self._check_for_messages)

    def send(self):
        text = self.entry.get().strip()
        if not text:
            return
        messages = read_json(CHAT_FILE, [])
        messages.append({
            "sender": self.me,
            "text": text,
            "time": datetime.now().strftime("%H:%M"),
        })
        write_json(CHAT_FILE, messages)
        self.entry.delete(0, "end")
        self._show(messages)

    def _check_for_messages(self):
        messages = read_json(CHAT_FILE, None)
        if messages is not None:
            self._show(messages)
        self.after(300, self._check_for_messages)

    def _show(self, messages):
        if messages == self._shown_messages:
            return
        # soft "pop" sound when the other person sends something (not when the window opens).
        if self._shown_messages is not None and len(messages) > len(self._shown_messages):
            new_messages = messages[len(self._shown_messages):]
            if any(message.get("sender") != self.me for message in new_messages):
                play_sound("message")
        self._shown_messages = list(messages)

        self.log.configure(state="normal")
        self.log.delete("0.0", "end")
        for message in messages:
            sender = message.get("sender", "?")
            name = "You" if sender == self.me else sender
            self.log.insert("end", f"[{message.get('time', '')}] {name}: ", sender)
            self.log.insert("end", f"{message.get('text', '')}\n")
        self.log.configure(state="disabled")
        self.log.see("end")
