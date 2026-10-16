import bpy
import os
from math import radians

context = bpy.context

models_path = "//"
render_path = "//"

models = ["model.obj", "model.obj"]

print(bpy.data.scenes)

# create a scene
scene = bpy.data.scenes[0]
camera_data = bpy.data.cameras[0]

camera = bpy.data.objects.new("Camera", camera_data)
camera.location = (-2.0, 3.0, 3.0)
camera.rotation_euler = ([radians(a) for a in (422.0, 0.0, 149)])
scene.objects.link(camera)

# do the same for lights etc
scene.update()

for model_path in models:
    scene.camera = camera
    path = os.path.join(models_path, model_path)
    # make a new scene with cam and lights linked
    context.screen.scene = scene
    bpy.ops.scene.new(type='LINK_OBJECTS')
    context.scene.name = model_path
    cams = [c for c in context.scene.objects if c.type == 'CAMERA']
    #import model
    bpy.ops.import_scene.obj(filepath=path, axis_forward='-Z', axis_up='Y', filter_glob="*.obj;*.mtl")
    for c in cams:
        context.scene.camera = c                                    
        print("Render ", model_path, context.scene.name, c.name)
        context.scene.render.filepath = "somepathmadeupfrommodelname"
        bpy.ops.render.render(write_still=True)