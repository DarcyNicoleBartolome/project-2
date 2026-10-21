# runs inside blender: places blendy and the numbered flags where the expert clicks.
# (see the README for how to start it and how it works.)
import json
import math
import os
import sys
import tempfile
import time

import bpy
import mathutils
from bpy_extras import view3d_utils


# same folder the GUIs use (SHARED_DIR in shared.py).
SHARED_DIR = os.path.join(tempfile.gettempdir(), "cpsc581_project2")
COMMAND_FILE = os.path.join(SHARED_DIR, "blender_commands.json")
STATUS_FILE = os.path.join(SHARED_DIR, "blender_status.json")

# collections that hold blendy and the flags. clicks on these are skipped, so a flag can't land on top of blendy.
# ("Tour Collection" isn't in the list, because the novice's model is in it.)
OUR_COLLECTIONS = {"Tour Guy", "Tour Guy Instance", "Flags", "Flag Instance", "Base Flag"}

# how far from a wall blendy stands when the expert clicks on the side of the model.
WALL_GAP = 0.7


# from blender code

def create_tour_guy(guy_x, guy_y,_guy_z, angle):
    # Ensure tour guy collection exists
    tour_guy = bpy.data.collections.get("Tour Guy")

    if tour_guy is None:
        tour_guy = bpy.data.collections.new("Tour Guy")
        bpy.context.scene.collection.children.link(tour_guy)

    # Delete old tour guy
    clear_tour_guy()

    # Create a tour guy instance
    bpy.ops.object.collection_instance_add(
        collection = 'Tour Guy Instance',
        align = 'WORLD',
        location = (guy_x, guy_y,_guy_z),
        rotation = (0, 0, angle),
        scale = (1, 1, 1)
    )

    instance = bpy.context.object
    instance.name = "Tour Guy Instance"

    # Move tour guy instance into the Tour Guy collection
    for col in list(instance.users_collection):
        col.objects.unlink(instance)

    tour_guy.objects.link(instance)



def create_flag(flag_x, flag_y, flag_z, angle):
    # Offset flag from guy
    distance = 2
    flag_x = flag_x - math.sin(angle) * distance
    flag_y = flag_y + math.cos(angle) * distance

    # Ensure flags collection exists
    flags = bpy.data.collections.get("Flags")

    if flags is None:
        flags = bpy.data.collections.new("Flags")
        bpy.context.scene.collection.children.link(flags)

    # Determine new flag number
    flag_count = count_flags(flags)

    # Create a flag instance
    bpy.ops.object.collection_instance_add(
        collection = "Flag Instance",
        align = "WORLD",
        location = (flag_x, flag_y, flag_z),
        rotation = (0, 0, angle),
        scale = (1, 1, 1)
    )

    instance = bpy.context.object
    instance.name = f"Flag_{flag_count:03d}"

    # Move flag instance into the Flags collection
    for col in list(instance.users_collection):
        col.objects.unlink(instance)

    flags.objects.link(instance)

    # Create text objects for flag
    for source_name in ("Text", "Text.001"):
        source = bpy.data.objects.get(source_name)

        # Copy the object and its data
        text = source.copy()
        text.data = source.data.copy()

        # Give the text a unique name and value
        text.name = f"Flag_{flag_count:03d}_{source_name}"
        text.data.body = str(flag_count)

        # Link the text to Flags
        flags.objects.link(text)

        # Position the text relative to the flag instance
        text.location = instance.location + (
            instance.rotation_euler.to_matrix() @ source.location
        )

        text.rotation_euler = source.rotation_euler
        text.rotation_euler.z += instance.rotation_euler.z


def count_flags(flags):
    # Find the largest existing flag number
    max_flag_number = 0

    for obj in flags.objects:
        if obj.name.startswith("Flag_"):
            # Get number from name
            parts = obj.name.split("_")

            try:
                flag_number = int(parts[1])
                max_flag_number = max(max_flag_number, flag_number)

            except (ValueError, IndexError):
                continue

    return max_flag_number + 1


def clear_flags():
    flags = bpy.data.collections.get("Flags")

    if flags:
        for obj in list(flags.objects):
            bpy.data.objects.remove(obj, do_unlink=True)


def clear_tour_guy():
    tour_guy = bpy.data.collections.get("Tour Guy")

    if tour_guy:
        for obj in list(tour_guy.objects):
            bpy.data.objects.remove(obj, do_unlink=True)


# finds the 3d view under the expert's click.
# (u, v) = where the expert clicked on the picture of blender's window (0 = left/top, 1 = right/bottom).
# returns (window, area, region, point inside the region), or None if the click wasn't on a 3d view.
def find_view3d(u, v):
    for window in bpy.context.window_manager.windows:
        # blender measures from the bottom-left corner of the window.
        x = u * window.width
        y = (1 - v) * window.height
        for area in window.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            for region in area.regions:
                if region.type != 'WINDOW':
                    continue
                if region.x <= x < region.x + region.width and region.y <= y < region.y + region.height:
                    return window, area, region, (x - region.x, y - region.y)
    return None


# True if obj is part of blendy or a flag (instead of the novice's model).
def is_ours(obj):
    return obj is not None and any(c.name in OUR_COLLECTIONS for c in obj.users_collection)


# shoots a ray into the scene, skipping blendy and the flags.
# returns (hit point, surface normal), or (None, None) if it hits nothing.
def cast_ray(origin, direction):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    for attempt in range(20):
        hit, location, normal, _, obj, _ = scene.ray_cast(depsgraph, origin, direction, distance=10000)
        if not hit:
            return None, None
        if not is_ours(obj):
            return location, normal
        # went through blendy or a flag, so keep going from just past it.
        origin = location + direction * 0.001
    return None, None


# where on the model the expert's click points to (or on the ground, z = 0, if it misses the model).
# returns (point, normal, hit_model).
def click_to_point(origin, direction):
    point, normal = cast_ray(origin, direction)
    if point is not None:
        return point, normal, True
    ground = mathutils.geometry.intersect_line_plane(
        origin, origin + direction, mathutils.Vector((0, 0, 0)), mathutils.Vector((0, 0, 1))
    )
    if ground is not None and (ground - origin).dot(direction) > 0:
        return ground, mathutils.Vector((0, 0, 1)), False
    return None, None, False


# rotation (around z) that makes blendy at source face target.
# (blendy faces +y when his rotation is 0, the same "in front of the guy" direction create_flag uses.)
def angle_towards(source, target):
    d = target - source
    return math.atan2(-d.x, d.y)


# where blendy should stand to show point.
# on a floor or the top of the model he stands right on it, on a wall he stands on the ground in front of it.
def standing_spot(point, normal):
    if normal.z >= 0.5:
        return point.copy()
    out = mathutils.Vector((normal.x, normal.y, 0))
    if out.length < 1e-6:
        out = mathutils.Vector((0, -1, 0))
    out.normalize()
    above = point + out * WALL_GAP + mathutils.Vector((0, 0, 0.1))
    below, _ = cast_ray(above, mathutils.Vector((0, 0, -1)))
    if below is not None:
        return below
    return mathutils.Vector((above.x, above.y, min(0.0, point.z)))


# animations (blendy hops into place, flags drop in with a bounce).
_tweens = []


def ease_out_cubic(t):
    return 1 - (1 - t) ** 3


def ease_out_bounce(t):
    if t < 1 / 2.75:
        return 7.5625 * t * t
    if t < 2 / 2.75:
        t -= 1.5 / 2.75
        return 7.5625 * t * t + 0.75
    if t < 2.5 / 2.75:
        t -= 2.25 / 2.75
        return 7.5625 * t * t + 0.9375
    t -= 2.625 / 2.75
    return 7.5625 * t * t + 0.984375


# moves obj smoothly to a new location (and turns it), with an optional hop.
def animate(obj, to_location, to_angle=None, duration=0.45, hop=0.0, ease=ease_out_cubic, from_location=None):
    start = from_location.copy() if from_location is not None else obj.location.copy()
    from_angle = obj.rotation_euler.z
    turn = 0.0
    if to_angle is not None:
        # turn the short way round.
        turn = (to_angle - from_angle + math.pi) % (2 * math.pi) - math.pi
    obj.location = start
    _tweens.append({
        "obj": obj, "from": start, "to": to_location.copy(),
        "from_angle": from_angle, "turn": turn,
        "hop": hop, "ease": ease, "start": time.perf_counter(), "duration": duration,
    })
    if not bpy.app.timers.is_registered(_animate_tick):
        bpy.app.timers.register(_animate_tick, first_interval=0)


def _animate_tick():
    now = time.perf_counter()
    for tween in list(_tweens):
        t = min(1.0, (now - tween["start"]) / tween["duration"])
        e = tween["ease"](t)
        try:
            location = tween["from"].lerp(tween["to"], e)
            location.z += tween["hop"] * math.sin(math.pi * t)
            tween["obj"].location = location
            tween["obj"].rotation_euler.z = tween["from_angle"] + tween["turn"] * e
        except ReferenceError:
            t = 1.0  # the object was deleted (e.g. by clear) while moving
        if t >= 1.0:
            _tweens.remove(tween)
    return 1 / 60 if _tweens else None  # None stops the timer until the next animation


# what the expert's buttons do.
def tour_guy_object():
    collection = bpy.data.collections.get("Tour Guy")
    if collection:
        for obj in collection.objects:
            return obj
    return None


# avatar tool: blendy hops over to the clicked spot and faces the novice's view.
def place_avatar(point, normal, camera):
    spot = standing_spot(point, normal)
    # face the camera (the person looking at the screen).
    angle = angle_towards(spot, camera) if normal.z >= 0.5 else angle_towards(spot, point)
    guy = tour_guy_object()
    if guy is None:
        create_tour_guy(spot.x, spot.y, spot.z, angle)
        guy = tour_guy_object()
        animate(guy, spot, angle, duration=0.5, from_location=spot + mathutils.Vector((0, 0, 2.5)),
                ease=ease_out_bounce)
    else:
        animate(guy, spot, angle, duration=0.55, hop=1.2)
    return "Blendy moved to the spot you clicked"


# marker tool: plants the next numbered flag where the expert clicked, and turns blendy to face it.
def place_flag(point, normal, camera):
    base = point + normal * 0.03
    # the flag's cloth sticks out sideways from the pole, so turn it a quarter turn
    # from "facing the camera" to show the cloth and its number face-on.
    angle = angle_towards(base, camera) + math.pi / 2

    # create_flag puts the flag 2 units in front of the position it gets,
    # so give it the spot 2 units behind where the flag should go.
    distance = 2
    create_flag(base.x + math.sin(angle) * distance, base.y - math.cos(angle) * distance, base.z, angle)

    flags = bpy.data.collections["Flags"]
    number = count_flags(flags) - 1
    # drop the flag and its number labels in from above.
    for obj in flags.objects:
        if obj.name == f"Flag_{number:03d}" or obj.name.startswith(f"Flag_{number:03d}_"):
            animate(obj, obj.location.copy(), duration=0.6, ease=ease_out_bounce,
                    from_location=obj.location + mathutils.Vector((0, 0, 3)))

    # blendy turns (with a little hop) to point at the new flag.
    guy = tour_guy_object()
    if guy is not None:
        animate(guy, guy.location.copy(), angle_towards(guy.location, base), duration=0.4, hop=0.4)
    return number


def clear_all():
    _tweens.clear()
    clear_flags()
    clear_tour_guy()


# carries out one command from the expert. returns (ok, message, flag number).
def handle_command(command):
    action = command.get("action")

    if action == "clear":
        clear_all()
        return True, "Removed Blendy and all flags", None

    if action not in ("avatar", "flag"):
        return False, f"Unknown command: {action}", None

    found = find_view3d(command["u"], command["v"])
    if found is None:
        return False, "Click on the 3D view (not the side panels)", None
    window, area, region, xy = found
    rv3d = area.spaces.active.region_3d

    with bpy.context.temp_override(window=window, area=area, region=region):
        if bpy.context.object is not None and bpy.context.object.mode != 'OBJECT':
            # objects can't be created in other modes
            bpy.ops.object.mode_set(mode='OBJECT')

        # the line from the viewport camera through the clicked pixel.
        origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, xy)
        direction = view3d_utils.region_2d_to_vector_3d(region, rv3d, xy)
        camera = rv3d.view_matrix.inverted().translation
        return place_at_click(action, origin, direction, camera)


# places blendy ("avatar") or a flag ("flag") where the click's line meets the model.
def place_at_click(action, origin, direction, camera):
    point, normal, hit_model = click_to_point(origin, direction)
    if point is None:
        return False, "Couldn't find anything there - click on the model", None

    if action == "avatar":
        return True, place_avatar(point, normal, camera), None
    number = place_flag(point, normal, camera)
    return True, f"Flag {number} placed", number


# listening for commands from the expert.
def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def write_json(path, data):
    os.makedirs(SHARED_DIR, exist_ok=True)
    tmp_path = f"{path}.blender.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        for attempt in range(10):
            try:
                os.replace(tmp_path, path)
                return
            except PermissionError:
                time.sleep(0.01)  # a GUI is reading it right now
    except OSError as exc:
        print(f"[listener] Could not write status: {exc}")


class Listener:
    def __init__(self):
        self.status = {"session": None, "last_id": 0, "ok": True, "event": None,
                       "flag_number": None, "message": "Blender is listening", "heartbeat": 0}
        self.last_heartbeat = 0
        # skip commands sent before the listener started, so restarting it doesn't replay old flags.
        data = read_json(COMMAND_FILE) or {}
        commands = data.get("commands", [])
        self.status["session"] = data.get("session")
        self.status["last_id"] = commands[-1]["id"] if commands else 0
        self.save_status()

    # if another copy of the listener is running too (e.g. the script was run twice), take over
    # what it already did, so no command is done twice (that would plant two flags in the same spot).
    def catch_up(self):
        shared = read_json(STATUS_FILE) or {}
        if shared.get("session") == self.status["session"] and shared.get("last_id", 0) > self.status["last_id"]:
            for key in ("last_id", "ok", "message", "event", "flag_number"):
                self.status[key] = shared.get(key)

    def save_status(self):
        self.catch_up()  # never overwrite newer news from another copy
        self.status["heartbeat"] = time.time()
        self.last_heartbeat = time.monotonic()
        write_json(STATUS_FILE, self.status)

    def poll(self):
        data = read_json(COMMAND_FILE)
        if data:
            if data.get("session") != self.status["session"]:
                # the expert GUI was restarted, so its command numbers start again at 1.
                self.status.update({"session": data.get("session"), "last_id": 0, "ok": True,
                                    "event": None, "flag_number": None,
                                    "message": "Expert window connected"})
                self.save_status()
            for command in data.get("commands", []):
                self.catch_up()
                if command.get("id", 0) <= self.status["last_id"]:
                    continue
                try:
                    ok, message, number = handle_command(command)
                except Exception as exc:
                    ok, message, number = False, f"Blender error: {exc}", None
                print(f"[listener] {command.get('action')}: {message}")
                self.status.update({
                    "last_id": command["id"], "ok": ok, "message": message,
                    "event": command.get("action") if ok else None, "flag_number": number,
                })
                self.save_status()

        # let the GUIs know blender is still listening.
        if time.monotonic() - self.last_heartbeat > 2:
            self.save_status()
        return 0.25  # check again in a quarter of a second


def start():
    # stops a listener from an earlier "Run Script", so there's only ever one.
    # it's remembered on sys because that lasts for the whole blender session, even when another
    # .blend file is opened (blender keeps the listener running across file loads but forgets most other things).
    old = getattr(sys, "_cpsc581_listener_poll", None)
    if old is not None and bpy.app.timers.is_registered(old):
        bpy.app.timers.unregister(old)

    listener = Listener()
    # keep this exact function: blender recognises a timer by the object it was registered with,
    # so this is what gets unregistered next time.
    poll = listener.poll
    sys._cpsc581_listener_poll = poll
    bpy.app.timers.register(poll, first_interval=0.25, persistent=True)
    print(f"[listener] Listening for the expert GUI (files in {SHARED_DIR})")
    return listener


if __name__ == "__main__":
    start()
