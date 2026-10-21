from tkinter import *
import time

import customtkinter as ctk
from CTkColorPicker import *

from shared import (
    BlenderCapture, BlenderCanvas, ChatPanel,
    CHAT_FILE, COMMAND_FILE, SHARED_DIR, STROKE_FILE,
    load_icon, read_blender_status, write_json,
)


# tool buttons: the selected tool is blue, the others are grey.
SELECTED_TOOL_COLOR = ctk.ThemeManager.theme["CTkButton"]["fg_color"]
SELECTED_TOOL_HOVER = ctk.ThemeManager.theme["CTkButton"]["hover_color"]
UNSELECTED_TOOL_COLOR = ("gray65", "gray28")
UNSELECTED_TOOL_HOVER = ("gray55", "gray35")

# colours for the "Blender: ..." status line under the avatar/marker buttons.
STATUS_COLORS = {"ok": "#1bce63", "info": ("gray40", "gray70"), "warn": "#fa9108"}


class Drawing(ctk.CTk):
    def __init__(self):
        super().__init__()

        # bright red, so it shows up on blender's dark grey background.
        self.drawingColor = "#ea1111"
        self.pen_size = 5
        # what clicking on the picture does ("brush", "eraser", "avatar" = move blendy there, "marker" = add a flag there).
        self.tool = "brush"

        # every line segment drawn so far, saved as positions on the blender picture (see BlenderCanvas in shared.py).
        self.stroke_data = []
        self.next_stroke_id = 0
        self.stroke_items = {}  # canvas line item -> stroke id (used by the eraser)
        self.last_point = None
        self._save_after_id = None

        # commands for blender (read by blender_listener.py).
        # the session number lets blender know when this window was restarted.
        self.blender_session = time.time()
        self.blender_commands = []
        self.blender_command_id = 0
        self.waiting_since = None  # when we sent a command blender hasn't done yet (None = not waiting)
        self.result_shown_at = 0   # when blender's last reply was shown

        # every session starts with a blank drawing, an empty chat and no commands.
        write_json(STROKE_FILE, [])
        write_json(CHAT_FILE, [])
        write_json(COMMAND_FILE, {"session": self.blender_session, "commands": []})
        print(f"Sharing drawings, chat and Blender commands through: {SHARED_DIR}")

        # set the window information
        self.title("Project 2 - Expert")
        self.geometry("1000x680")
        self.minsize(850, 600)

        # layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)

        # left
        self.left = ctk.CTkFrame(self, corner_radius=16)
        self.left.grid(row=0, column=0, padx=(18, 10), pady=(18, 10), sticky="ns")

        self.clear_button = ctk.CTkButton(
            self.left, text="Clear Canvas", image=load_icon("delete.png"), command=self.clear_canvas,
        )
        self.clear_button.grid(row=1, column=0, padx=12, pady=9)

        # drawing tools (brush and eraser side by side).
        self.tool_buttons = {}
        self.tool_row = ctk.CTkFrame(self.left, fg_color="transparent")
        self.tool_row.grid(row=3, column=0, padx=12, pady=9)
        self.add_tool_button(self.tool_row, "brush", "Brush", column=0)
        self.add_tool_button(self.tool_row, "eraser", "Eraser", column=1)

        self.colorbutton = ctk.CTkButton(
            self.left, text="CHOOSE COLOR", text_color="black",
            fg_color=self.drawingColor, hover_color=self.drawingColor, command=self.ask_color,
        )
        self.colorbutton.grid(row=4, column=0, padx=12, pady=6)

        self.pen_size_label = ctk.CTkLabel(self.left, text=f"Pen Size: {self.pen_size}", corner_radius=0)
        self.pen_size_label.grid(row=5, column=0, padx=12, pady=2)
        self.pen_size_slider = ctk.CTkSlider(
            self.left, from_=1, to=50, number_of_steps=49, command=self.set_pen_size,
        )
        self.pen_size_slider.grid(row=6, column=0, padx=12, pady=2)
        self.pen_size_slider.set(self.pen_size)

        # blender tools (avatar = click to move blendy there, marker = click to add a numbered flag there).
        self.blender_row = ctk.CTkFrame(self.left, fg_color="transparent")
        self.blender_row.grid(row=7, column=0, padx=12, pady=(22, 4))
        self.add_tool_button(self.blender_row, "avatar", "Avatar", column=0)
        self.add_tool_button(self.blender_row, "marker", "Marker", column=1)

        self.clear_blender_button = ctk.CTkButton(
            self.left, text="Clear Avatar & Markers", image=load_icon("delete.png"), command=self.clear_blender,
        )
        self.clear_blender_button.grid(row=8, column=0, padx=12, pady=4)

        self.blender_status = ctk.CTkLabel(
            self.left, text="Blender: checking...", wraplength=200, justify="center",
            font=ctk.CTkFont(size=12), text_color=STATUS_COLORS["info"],
        )
        self.blender_status.grid(row=9, column=0, padx=8, pady=(0, 4))

        # chat with the novice (see ChatPanel in shared.py).
        self.chat = ChatPanel(self.left, me="Expert", other="novice")
        self.chat.grid(row=10, column=0, padx=8, pady=(8, 10))

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
        self.canvas = BlenderCanvas(
            self.preview, self.capture, on_picture_moved=self.redraw_strokes, cursor="crosshair",
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Button-1>", self.start_stroke)
        self.canvas.bind("<B1-Motion>", self.draw_stroke)
        self.canvas.bind("<ButtonRelease-1>", self.end_stroke)
        self.canvas.bind("<Motion>", self.move_size_preview)
        self.canvas.bind("<Leave>", lambda event: self.canvas.itemconfigure(self.size_preview, state=HIDDEN))

        # circle that follows the mouse to show the brush/eraser size.
        self.size_preview = self.canvas.create_oval(0, 0, 0, 0, width=1, state=HIDDEN)

        self.set_tool("brush")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(300, self.check_blender_status)

    def add_tool_button(self, parent, tool, text, column):
        button = ctk.CTkButton(
            parent, text=text, width=68, image=load_icon(f"{tool}.png"),
            command=lambda: self.set_tool(tool),
        )
        button.grid(row=0, column=column, padx=(0, 4) if column == 0 else 0)
        self.tool_buttons[tool] = button

    # user clicked on the picture: start a line, erase, or place something in blender (depends on the tool).
    def start_stroke(self, event):
        if self.tool in ("avatar", "marker"):
            self.place_in_blender(event)
            return
        self.last_point = (event.x, event.y)
        if self.tool == "eraser":
            self.erase_at(event.x, event.y)

    # user is dragging the mouse: add the next line segment, or keep erasing.
    def draw_stroke(self, event):
        if self.tool not in ("brush", "eraser"):
            return
        self.move_size_preview(event)

        if self.tool == "eraser":
            self.erase_at(event.x, event.y)
            return
        # nothing to draw on until the first picture of blender has arrived.
        if self.last_point is None or self.canvas.picture_rect is None:
            return

        start = self.canvas.to_picture(*self.last_point)
        end = self.canvas.to_picture(event.x, event.y)
        stroke = {
            "type": "stroke",
            "id": self.next_stroke_id,
            "x1": start[0],
            "y1": start[1],
            "x2": end[0],
            "y2": end[1],
            "color": self.drawingColor,
            # thickness as a fraction of the picture width, so it scales too.
            "width": self.pen_size / self.canvas.picture_rect[2],
        }
        self.next_stroke_id += 1
        self.stroke_data.append(stroke)

        item = self.canvas.draw_segment(stroke, tags="line")
        self.stroke_items[item] = stroke["id"]
        self.canvas.tag_raise(self.size_preview)

        self.last_point = (event.x, event.y)
        self.schedule_save()

    def end_stroke(self, event):
        if self.last_point is not None:
            self.last_point = None
            self.save_strokes()

    # deletes every line segment under the eraser circle.
    def erase_at(self, x, y):
        radius = max(self.pen_size / 2, 4)
        erased = set()
        for item in self.canvas.find_overlapping(x - radius, y - radius, x + radius, y + radius):
            stroke_id = self.stroke_items.pop(item, None)
            if stroke_id is not None:  # skips the blender picture and the size circle
                self.canvas.delete(item)
                erased.add(stroke_id)

        if erased:
            self.stroke_data = [stroke for stroke in self.stroke_data if stroke["id"] not in erased]
            self.schedule_save()

    # the blender picture moved or changed size, so redraw every line in its new spot.
    def redraw_strokes(self):
        self.canvas.delete("line")
        self.stroke_items.clear()
        for stroke in self.stroke_data:
            item = self.canvas.draw_segment(stroke, tags="line")
            self.stroke_items[item] = stroke["id"]
        self.canvas.tag_raise(self.size_preview)

    def clear_canvas(self):
        self.canvas.delete("line")
        self.stroke_items.clear()
        self.stroke_data.clear()
        self.save_strokes()

    # saves the strokes for the novice at most 20 times a second while drawing.
    def schedule_save(self):
        if self._save_after_id is None:
            self._save_after_id = self.after(50, self.save_strokes)

    def save_strokes(self):
        if self._save_after_id is not None:
            self.after_cancel(self._save_after_id)
            self._save_after_id = None
        write_json(STROKE_FILE, self.stroke_data)

    def set_tool(self, tool):
        self.tool = tool
        for name, button in self.tool_buttons.items():
            selected = name == tool
            button.configure(
                fg_color=SELECTED_TOOL_COLOR if selected else UNSELECTED_TOOL_COLOR,
                hover_color=SELECTED_TOOL_HOVER if selected else UNSELECTED_TOOL_HOVER,
            )
        # crosshair for drawing, pointing hand for placing things in blender.
        self.canvas.configure(cursor="crosshair" if tool in ("brush", "eraser") else "hand2")
        self.canvas.itemconfigure(self.size_preview, state=HIDDEN)
        self.update_size_preview_style()

    def ask_color(self):
        pick_color = AskColor() # open the color picker
        color = pick_color.get() # get the color string
        if not color:  # the picker was closed without choosing
            return
        self.colorbutton.configure(fg_color=color, hover_color=color)
        self.drawingColor = color
        # picking a colour means the user wants to draw, so switch back to the brush.
        self.set_tool("brush")

    def set_pen_size(self, value):
        self.pen_size = int(value)
        self.pen_size_label.configure(text=f"Pen Size: {self.pen_size}")

    # moves the size circle to the mouse (only for the brush and eraser).
    def move_size_preview(self, event):
        if self.tool not in ("brush", "eraser"):
            return
        radius = max(self.pen_size / 2, 4) if self.tool == "eraser" else max(self.pen_size / 2, 1)
        self.canvas.coords(
            self.size_preview,
            event.x - radius, event.y - radius, event.x + radius, event.y + radius,
        )
        self.canvas.itemconfigure(self.size_preview, state=NORMAL)
        self.canvas.tag_raise(self.size_preview)

    # solid circle in the drawing colour for the brush, dashed white circle for the eraser.
    def update_size_preview_style(self):
        if self.tool == "eraser":
            self.canvas.itemconfigure(self.size_preview, outline="white", dash=(3, 2))
        else:
            self.canvas.itemconfigure(self.size_preview, outline=self.drawingColor, dash="")

    # avatar or marker tool: sends the clicked spot to blender.
    def place_in_blender(self, event):
        if self.canvas.picture_rect is None:
            return
        u, v = self.canvas.to_picture(event.x, event.y)
        if not (0 <= u <= 1 and 0 <= v <= 1):
            self.show_blender_status("Click on the picture of Blender", "warn")
            return
        action = "avatar" if self.tool == "avatar" else "flag"
        self.send_blender_command(action, u=u, v=v)
        self.show_click_ping(event.x, event.y)

    def clear_blender(self):
        self.send_blender_command("clear")

    def send_blender_command(self, action, **details):
        self.blender_command_id += 1
        self.blender_commands.append({"id": self.blender_command_id, "action": action, **details})
        self.blender_commands = self.blender_commands[-50:]  # blender only needs the recent ones
        write_json(COMMAND_FILE, {"session": self.blender_session, "commands": self.blender_commands})
        self.waiting_since = time.monotonic()
        self.show_blender_status("Sending to Blender...", "info")

    # shows what blender did with the last command, or whether it's listening.
    def check_blender_status(self):
        if not self.winfo_exists():
            return
        status, connected = read_blender_status()
        done = (
            status is not None
            and status.get("session") == self.blender_session
            and status.get("last_id", 0) >= self.blender_command_id
        )

        if self.waiting_since is not None:
            if done:
                self.waiting_since = None
                self.result_shown_at = time.monotonic()
                self.show_blender_status(status.get("message", "Done"), "ok" if status.get("ok") else "warn")
            elif time.monotonic() - self.waiting_since > 3:
                self.show_blender_status(
                    "Blender isn't responding. In Blender, run blender_listener.py (see README).", "warn")
        elif time.monotonic() - self.result_shown_at > 4:
            if connected:
                self.show_blender_status("Blender: connected", "ok")
            else:
                self.show_blender_status(
                    "Blender: not connected. In Blender, run blender_listener.py (see README).", "warn")

        self.after(300, self.check_blender_status)

    def show_blender_status(self, text, kind):
        self.blender_status.configure(text=text, text_color=STATUS_COLORS[kind])

    # ring that grows where the expert clicked, so they can see the click was sent.
    def show_click_ping(self, x, y, step=0, ring=None):
        if ring is None:
            ring = self.canvas.create_oval(x, y, x, y, outline="#ffb454", width=3)
        radius = 4 + step * 4
        self.canvas.coords(ring, x - radius, y - radius, x + radius, y + radius)
        self.canvas.itemconfigure(ring, width=max(1, 3 - step // 3))
        if step < 8:
            self.after(30, lambda: self.show_click_ping(x, y, step + 1, ring))
        else:
            self.canvas.delete(ring)

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
