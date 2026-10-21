from tkinter import *
import customtkinter as ctk

from shared import (
    BlenderCapture, BlenderCanvas, ChatPanel, STROKE_FILE,
    play_sound, read_blender_status, read_json,
)


class Drawing(ctk.CTk):
    def __init__(self):
        super().__init__()

        # the expert's strokes, as last read from stroke.json
        self.last_json_data = None

        # set the window information
        self.title("Project 2 - Novice")
        self.geometry("1000x650")
        self.minsize(850, 560)

        # layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)

        # left: chat with the expert (see ChatPanel in shared.py)
        self.left = ctk.CTkFrame(self, corner_radius=16)
        self.left.grid(row=0, column=0, padx=(18, 10), pady=(18, 10), sticky="ns")
        self.chat = ChatPanel(self.left, me="Novice", other="expert")
        self.chat.grid(row=0, column=0, padx=8, pady=12)

        # screen / preview
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

        # live picture of blender, with the expert's drawing on top.
        self.capture = BlenderCapture()
        self.canvas = BlenderCanvas(self.preview, self.capture, on_picture_moved=self.redraw_strokes)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # the last thing blender reported doing, so each new flag is only announced once
        # (and nothing old is announced when this window opens).
        status, _ = read_blender_status()
        self.last_blender_event = self.event_key(status)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(100, self.load_strokes)
        self.after(300, self.check_blender_events)

    # checks stroke.json for new strokes from the expert 10 times a second.
    def load_strokes(self):
        if not self.winfo_exists():
            return

        strokes = read_json(STROKE_FILE, None)
        # only redraw when the json data changes.
        if strokes is not None and strokes != self.last_json_data:
            self.last_json_data = strokes
            self.redraw_strokes()

        self.after(100, self.load_strokes)

    # draws the expert's strokes over the blender picture.
    # also called when the picture moves or changes size, so the lines stay on the same spot of the model.
    def redraw_strokes(self):
        self.canvas.delete("annotation")
        if self.canvas.picture_rect is None or not self.last_json_data:
            return
        for stroke in self.last_json_data:
            try:
                self.canvas.draw_segment(stroke, tags="annotation")
            except (KeyError, TypeError, ValueError):
                continue  # skip anything that isn't a valid stroke

    @staticmethod
    def event_key(status):
        return None if status is None else (status.get("session"), status.get("last_id"))

    # when the expert moves blendy or adds a flag, play a sound and show a message,
    # so the novice knows where to look.
    def check_blender_events(self):
        if not self.winfo_exists():
            return
        status, _ = read_blender_status()
        key = self.event_key(status)
        if key is not None and key != self.last_blender_event:
            self.last_blender_event = key
            event = status.get("event")
            if event == "flag":
                play_sound("flag")
                self.canvas.show_toast(f"Your expert planted flag {status.get('flag_number')} - Blendy is pointing at it")
            elif event == "avatar":
                play_sound("avatar")
                self.canvas.show_toast("Blendy hopped over to show you something", color="#6cb6ff")
            elif event == "clear":
                self.canvas.show_toast("Your expert cleared Blendy and the flags", color="#9a9a9a")
        self.after(300, self.check_blender_events)

    def on_close(self):
        self.capture.stop()
        self.destroy()


# starting the client
def start_screen():
   # start GUI
   app = Drawing()
   app.mainloop()

if __name__ == "__main__":
   start_screen()
