import bpy
import bmesh
import gpu
from gpu_extras.batch import batch_for_shader
from mathutils import Vector
from bpy_extras import view3d_utils

_fur_draw_handle = None  # Global draw handler reference

def draw_fur_callback(self, context):
    """Draw a line from the face center to the current mouse intersection point."""
    if not self.face_center or not self.current_point:
        return

    shader = gpu.shader.from_builtin('3D_UNIFORM_COLOR')
    coords = [self.face_center, self.current_point]
    batch = batch_for_shader(shader, 'LINES', {"pos": coords})
    shader.bind()
    # Draw in a bright color (magenta)
    shader.uniform_float("color", (1.0, 0.0, 1.0, 1.0))
    batch.draw(shader)

class Mark_Directional_Material_Dialog(bpy.types.Operator):
    """Adjust the fur (grain) direction and store it on the active face using Mesh Attributes."""
    bl_idname = "mesh.material_direction_dialog"
    bl_label = "Adjust Fur Direction"
    bl_options = {'REGISTER', 'UNDO'}

    direction: bpy.props.FloatVectorProperty(
        name="Fur Direction",
        description="Fine-tune the fur direction (in local space)",
        subtype='DIRECTION',
        default=(0.0, 0.0, 1.0)
    )

    face_index: bpy.props.IntProperty()

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "direction", text="Direction")

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Active object is not a mesh.")
            return {'CANCELLED'}

        # Switch to Object Mode to ensure attribute data is allocated.
        bpy.ops.object.mode_set(mode='OBJECT')
        mesh = obj.data

        from mathutils import Vector
        dir_norm = Vector(self.direction).normalized()

        # If the attribute already exists, check if its data length is valid.
        if "material_direction" in mesh.attributes:
            attr = mesh.attributes["material_direction"]
            # If data is empty, remove and recreate it.
            if len(attr.data) == 0:
                mesh.attributes.remove(attr)
                attr = mesh.attributes.new(name="material_direction", type='FLOAT_VECTOR', domain='FACE')
        else:
            attr = mesh.attributes.new(name="material_direction", type='FLOAT_VECTOR', domain='FACE')

        # Force a mesh update (if needed)
        mesh.update()

        # Check that the attribute data length matches the number of polygons.
        if len(attr.data) < len(mesh.polygons):
            # If for some reason it's still not populated, remove and re-create.
            mesh.attributes.remove(attr)
            attr = mesh.attributes.new(name="material_direction", type='FLOAT_VECTOR', domain='FACE')

        if self.face_index >= len(attr.data):
            self.report({'ERROR'}, f"Face index {self.face_index} is out of range for attribute data (size {len(attr.data)}).")
            return {'CANCELLED'}

        # Set the value for the given face.
        attr.data[self.face_index].vector = dir_norm
        self.report({'INFO'}, f"Material direction set to {dir_norm} on face {self.face_index}.")

        # (Optionally switch back to Edit Mode if needed)
        bpy.ops.object.mode_set(mode='EDIT')
        return {'FINISHED'}


    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
class Mark_Directional_Material(bpy.types.Operator):
    """Draw a line on the active face to mark a direction that should represent directional sewing materials such as Fur grains."""
    bl_idname = "mesh.mark_directional_material"
    bl_label = "Mark Directional Material Properties"
    bl_options = {'REGISTER', 'UNDO'}

    # Property to pass the computed direction to the dialog operator
    computed_direction: bpy.props.FloatVectorProperty(
        name="Material Direction",
        description="Material Direction computed from mouse input (in local space)",
        subtype='DIRECTION',
        default=(0.0, 0.0, 1.0)
    )

    # Store the face index for later reference
    face_index: bpy.props.IntProperty()

    def __init__(self):
        self.object = None
        self.face_center = None
        self.current_point = None
        self._handle = None

    def invoke(self, context, event):
        # Verify active mesh in Edit Mode and an active face is selected
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Active object is not a mesh.")
            return {'CANCELLED'}
        if obj.mode != 'EDIT':
            self.report({'ERROR'}, "Object must be in Edit Mode.")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        face = bm.faces.active
        if not face:
            self.report({'ERROR'}, "No active face selected.")
            return {'CANCELLED'}

        self.object = obj
        self.face_index = face.index
        # Calculate the face center in world space
        local_center = face.calc_center_median()
        self.face_center = obj.matrix_world @ local_center

        # Add draw handler to display the temporary line
        global _fur_draw_handle
        _fur_draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            draw_fur_callback, (self, context), 'WINDOW', 'POST_VIEW'
        )
        self._handle = _fur_draw_handle

        context.window_manager.modal_handler_add(self)
        self.report({'INFO'}, "Drag the mouse to define fur direction. Left-click to confirm, right-click/Esc to cancel.")
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel(context)
            self.report({'INFO'}, "Fur direction drawing cancelled.")
            return {'CANCELLED'}

        if event.type == 'MOUSEMOVE':
            region = context.region
            rv3d = context.region_data
            coord = (event.mouse_region_x, event.mouse_region_y)
            ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
            ray_target = view3d_utils.region_2d_to_location_3d(region, rv3d, coord, Vector((0, 0, 1)))
            direction = (ray_target - ray_origin).normalized()

            # Raycast onto our object
            depsgraph = context.evaluated_depsgraph_get()

            result, loc, normal, index, hit_obj, matrix = context.scene.ray_cast(
                depsgraph,
                ray_origin,
                direction,
                distance=10000.0
            )

            if result and hit_obj == self.object:
                self.current_point = loc
            else:
                self.current_point = ray_target

            context.area.tag_redraw()

        # When the user confirms the direction with a left-click release:
        if event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            if not self.current_point:
                self.report({'WARNING'}, "No valid point defined.")
                return {'RUNNING_MODAL'}
            # Compute the direction vector in local space:
            mat_inv = self.object.matrix_world.inverted_safe()
            center_local = mat_inv @ self.face_center
            point_local = mat_inv @ self.current_point
            computed = (point_local - center_local).normalized()
            self.computed_direction = computed

            # Remove the draw handler
            self.finish(context)
            # Now call the dialog operator to allow fine-tuning:
            bpy.ops.mesh.material_direction_dialog('INVOKE_DEFAULT',
                                                direction=self.computed_direction,
                                                face_index=self.face_index)
            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def finish(self, context):
        global _fur_draw_handle
        if self._handle is not None:
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            self._handle = None
            _fur_draw_handle = None
        context.area.tag_redraw()

    def cancel(self, context):
        self.finish(context)