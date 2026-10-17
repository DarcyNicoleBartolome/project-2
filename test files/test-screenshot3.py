from ScreenCaptureKit import (
    SCContentFilter,
    SCShareableContent,
    SCScreenshotManager,
    SCStreamConfiguration,
)
from AppKit import NSBitmapImageRep, NSPNGFileType
from PyObjCTools import AppHelper

def content_ready(content, error):
    if error:
        print("Window-list error:", error)
        AppHelper.stopEventLoop()
        return

   #  windows = list(content.applications())
    windows = list(content.windows())
    print(f"Found {len(windows)} windows")
    for window in windows:
        print("Window:", repr(window.title()), "on screen:", window.isOnScreen())
      #   print(window.applicationName())

    blender = next(
        (
            w for w in windows
            # if "discord" in (w.applicationName() or "").lower()
            if w.isOnScreen() and "discord" in (w.title() or "").lower()
        ),
        None,
    )

    if blender is None:
        print("No on-screen window title contains 'Blender'.")
        AppHelper.stopEventLoop()
        return

   #  print("Capturing:", blender.applicationName())
    print("Capturing:", blender.title())

   #  content_filter = (
   #      SCContentFilter.alloc()
   #      .initWithDesktopIndependentWindow_(blender)
   #  )

    content_filter = SCContentFilter.alloc().init()
    content_filter.initWithDesktopIndependentWindow_(blender)

    print("content filter success")
    config = SCStreamConfiguration.alloc().init()
    config.setWidth_(max(1, int(blender.frame().size.width)))
    config.setHeight_(max(1, int(blender.frame().size.height)))

    def screenshot_ready(cg_image, error):
        if error:
            print("Screenshot error:", error)
        elif cg_image is None:
            print("Capture returned no image.")
        else:
            bitmap = NSBitmapImageRep.alloc().initWithCGImage_(cg_image)
            png_data = bitmap.representationUsingType_properties_(NSPNGFileType, {})
            ok = png_data.writeToFile_atomically_("blender.png", True)
            print("Saved blender.png" if ok else "Could not write blender.png")

        AppHelper.stopEventLoop()

    SCScreenshotManager.captureImageWithFilter_configuration_completionHandler_(
        content_filter, config, screenshot_ready
    )

print("Requesting window list…")
SCShareableContent.getShareableContentWithCompletionHandler_(content_ready)
AppHelper.runConsoleEventLoop()
