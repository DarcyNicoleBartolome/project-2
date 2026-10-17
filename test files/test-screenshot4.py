import tkinter as tk
from PIL import Image, ImageTk
import io


from ScreenCaptureKit import (
    SCContentFilter,
    SCShareableContent,
    SCScreenshotManager,
    SCStreamConfiguration,
)
from AppKit import NSBitmapImageRep


root = tk.Tk()
root.title("Blender window capture")
preview = tk.Label(root, text="Looking for Blender…")
preview.pack()

# Retain these objects while capture is running.
state = {"filter": None, "config": None, "busy": False, "stopped": False}


def show_capture(cg_image):
    """Convert a macOS CGImage screenshot to a Pillow image."""
    bitmap = NSBitmapImageRep.alloc().initWithCGImage_(cg_image)

    width = bitmap.pixelsWide()
    height = bitmap.pixelsHigh()

    # Let AppKit produce PNG data so we don't need to guess
    # the raw pixel channel order or row padding.
    from AppKit import NSBitmapImageFileTypePNG

    png_data = bitmap.representationUsingType_properties_(
        NSBitmapImageFileTypePNG, {}
    )

    image = Image.open(io.BytesIO(bytes(png_data))).convert("RGB")

    image.thumbnail((900, 600))

    photo = ImageTk.PhotoImage(image)
    preview.configure(image=photo, text="")
    preview.image = photo


def capture_next():
    if state["stopped"] or state["filter"] is None or state["busy"]:
        return

    state["busy"] = True

    def image_ready(cg_image, error):
        state["busy"] = False
        if error:
            print("Screenshot error:", error)
        elif cg_image:
            show_capture(cg_image)

        if not state["stopped"]:
            root.after(100, capture_next)  # Request another frame in ~100 ms.

    SCScreenshotManager.captureImageWithFilter_configuration_completionHandler_(
        state["filter"], state["config"], image_ready
    )


def content_ready(content, error):
    if error:
        preview.configure(text=f"Could not list windows: {error}")
        return

    # Pick the first on-screen Blender window. Print titles to help identify it.
    windows = list(content.windows())
    for window in windows:
        print("Window:", window.title())

    blender_window = next(
        (
            window for window in windows
            if window.isOnScreen() and "discord" in (window.title() or "").lower()
        ),
        None,
    )

    if blender_window is None:
        preview.configure(text="No on-screen Blender window found.")
        return

    # A display-independent filter follows the selected window between displays.
    state["filter"] = SCContentFilter.alloc().initWithDesktopIndependentWindow_(
        blender_window
    )
    state["config"] = SCStreamConfiguration.alloc().init()
    state["config"].setWidth_(blender_window.frame().size.width)
    state["config"].setHeight_(blender_window.frame().size.height)

    capture_next()


def close():
    state["stopped"] = True
    root.destroy()


root.protocol("WM_DELETE_WINDOW", close)

SCShareableContent.getShareableContentWithCompletionHandler_(content_ready)
root.mainloop()
