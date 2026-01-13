import bpy
from os.path import basename
from xml.sax.saxutils import escape
from bpy.props import (
    StringProperty,
    BoolProperty,
    EnumProperty,
    IntVectorProperty,
    FloatProperty,
)
import bmesh
import mathutils
import random

class Export_Sewingpattern(bpy.types.Operator):
    """Export Sewingpattern to .SVG file format. This should be called after the Seams to Sewing Pattern operator"""

    bl_idname = "object.export_sewingpattern"
    bl_label = "Export Sewing Pattern"
    bl_options = {'REGISTER', 'UNDO'}
    current_alignment_number = 0

    filepath: StringProperty(
        subtype='FILE_PATH',
    )
    alignment_markers: EnumProperty(
        items=(
            ('OFF', "Off",
             "No alignment markers"),
            ('SEAM', "Marked as seam",
             "Use sewing edges manually marked as seam"),
            ('AUTO', "Autodetect + seam",
             "Finds sewing edges of corners automatically and marks them as seam"),
        ),
        name="Alignment markers",
        description="Exports matching colored lines on the borders of sewing patterns to assist with alignment",
        default='AUTO',
    )
    alignment_numbers: bpy.props.BoolProperty(name="Alignment Numbers", default=True)
    aligment_number_font_size: bpy.props.FloatProperty(name="Font Size", default=12.0)
    show_peice_ids: bpy.props.BoolProperty(name="Piece IDs", default=True)
    piece_id_font_size: bpy.props.FloatProperty(name="Piece Label Size", default=30.0)
    file_format: EnumProperty(
        items=(
            ('SVG', "Scalable Vector Graphic (.svg)",
             "Export the sewing pattern to a .SVG file"),
        ),
        name="Format",
        description="File format to export the UV layout to",
        default='SVG',
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and obj.data.uv_layers

    def invoke(self, context, event):
        #stuff to check / set before goes here :)
        self.filepath = self.get_default_file_name(context) + "." + self.file_format.lower()
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def get_default_file_name(self, context):
        return context.active_object.name

    def check(self, context):
        if any(self.filepath.endswith(ext) for ext in (".png", ".eps", ".svg")):
            self.filepath = self.filepath[:-4]

        ext = "." + self.file_format.lower()
        self.filepath = bpy.path.ensure_ext(self.filepath, ext)
        return True

    def execute(self, context):
        obj = context.active_object
        is_editmode = (obj.mode == 'EDIT')
        if is_editmode:
            bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        filepath = self.filepath
        filepath = bpy.path.ensure_ext(filepath, "." + self.file_format.lower())
        
        if (self.alignment_markers == 'AUTO'):
            self.auto_detect_markers()

        self.export(filepath)

        if is_editmode:
            bpy.ops.object.mode_set(mode='EDIT', toggle=False)

        return {'FINISHED'}
    
    def get_piece_name(self,n):
        result = []
        while n > 0:
            n -= 1
            result.append(chr(n % 26 + ord('A')))
            n //= 26
        return ''.join(result[::-1])

    def export(self, filepath):
        #get loops:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type="FACE")

        obj = bpy.context.edit_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        document_scale = 1000.0 #millimeter
        document_scale *= obj["S2S_UVtoWORLDscale"]

        self.current_alignment_number = 0
        alignment_number_dictionary = dict()
        position_dictionary = dict()
        piece_dictionary = dict()
        letters = "abcdefghijklmnopqrstuvwyxtuv".upper()
        current_letter = 0

        svgstring = '<svg xmlns="http://www.w3.org/2000/svg"\n viewBox="0 0 ' + str(document_scale) + ' ' + str(document_scale) +'"\n'
        svgstring += 'width="' + str(document_scale) + 'mm" height="' + str(document_scale) + 'mm">'
        #svgstring += '<!-- Exported using the Seams to Sewing pattern for Blender  -->'
        svgstring += '\n<defs><style>.seam{stroke: #000; stroke-width:1px; fill:white} .sewinguide{stroke-width:1px;}</style></defs>'

        face_groups = []
        faces = set(bm.faces[:])
        while faces:
            bpy.ops.mesh.select_all(action='DESELECT')
            face = faces.pop()
            face.select = True
            bpy.ops.mesh.select_linked()
            selected_faces = {f for f in faces if f.select}
            selected_faces.add(face) # this or bm.faces above?
            face_groups.append(selected_faces)
            faces -= selected_faces

        print('Loop groups for sewing pattern export: ' + str(len(face_groups)))

        for fg in face_groups:

            bpy.ops.mesh.select_all(action='DESELECT')
            for f in fg:
                f.select = True

            bpy.ops.mesh.region_to_loop()

            boundary_loop = [e for e in bm.edges if e.select]
    
            relevant_loops=[]

            for e in boundary_loop:
                relevant_loops.append(e.link_loops[0])
        
            loop_groups = [[]]

            while (len(relevant_loops) > 0):
                temp_group = [relevant_loops[0]]
                vertex_to_match = relevant_loops[0].link_loop_next.vert
                relevant_loops.remove(relevant_loops[0])
                match = True
                while(match == True):
                    match = False
                    for x in range(0, len(relevant_loops)):
                        if (relevant_loops[x].link_loop_next.vert == vertex_to_match):
                            temp_group.append(relevant_loops[x])
                            vertex_to_match = relevant_loops[x].vert
                            relevant_loops.remove(relevant_loops[x])
                            match = True
                            break
                        if (relevant_loops[x].vert == vertex_to_match):
                            temp_group.append(relevant_loops[x])
                            vertex_to_match = relevant_loops[x].link_loop_next.vert
                            relevant_loops.remove(relevant_loops[x])
                            match = True
                            break
                loop_groups.append(temp_group)

            uv_layer = bm.loops.layers.uv.active
            
            #print border

            svgstring += '\n<g>'
            svgstring += '<path class="seam" d="'

            center_x = 0
            center_y = 0
            number_of_points = 0

            for lg in loop_groups:
                if (len(lg) == 0):
                    continue
                lg.append(lg[0])

                svgstring += 'M '

                for l in lg:
                    uv = l[uv_layer].uv.copy()
                    x = uv.x*document_scale
                    y = (1-uv.y)*document_scale
                    center_x += x
                    center_y += y
                    number_of_points += 1
                    svgstring += str(x)
                    svgstring += ','
                    svgstring += str(y)
                    svgstring += ' '

            svgstring += '"/>'
            
            center_x = center_x/number_of_points
            center_y = center_y/number_of_points

            current_letter = (current_letter + 1)
            letter = self.get_piece_name(current_letter)

            if self.show_peice_ids:
                svgstring += self.add_text(center_x,center_y,self.piece_id_font_size,str(letter))

            #print markers
            marker_list = []

            for lg in loop_groups:
                #markers
                if (self.alignment_markers != 'OFF'):
                    for l in lg:
                        has_wire = False
                        for w in l.vert.link_edges:
                            if w.is_wire and w.seam:
                                has_wire = True
                                maybe_marker = self.add_alignment_marker(l, w, uv_layer, document_scale, alignment_number_dictionary, position_dictionary, marker_list,None)
                                if maybe_marker[0] is True:
                                    marker_list.append(maybe_marker[1])

            for marker in marker_list:
                svgstring += marker.text

            svgstring += '</g>'

        svgstring += '\n</svg>'
        
        with open(filepath, "w") as file:
            file.write(svgstring)
            
        bpy.ops.object.mode_set(mode='OBJECT')
    
    class Marker:
        def __init__(self, parent, x, y, fontSize, text, id, loop, wire, uv_layer, document_scale, alignment_number_dictionary, position_dictionary, marker_list):
            self.parent = parent
            self.id = id
            self.loop = loop
            self.wire = wire
            self.uv_layer = uv_layer
            self.text = text
            self.x = x
            self.y = y
            self.fontSize = fontSize
            self.document_scale = document_scale
            self.alignment_number_dictionary = alignment_number_dictionary
            self.position_dictionary = position_dictionary
            self.marker_list = marker_list
            self.recalculate()

        def recalculate(self):
            # coordinate system is top left
            # 0,0 1,0
            # 0,1 1,1

            # text anchor is top left

            lower_y = self.y + (self.fontSize * 1.1) 
            lower_right_x = self.x + (self.fontSize * len(str(self.id)) * 0.702)
            self.upper_right_point = (lower_right_x, self.y)
            self.upper_left_point = (self.x, self.y)
            self.lower_right_point = (lower_right_x, lower_y)
            self.lower_left_point = (self.x,lower_y)

        def resize(self, newFontSize):
            if newFontSize < 1:
                return
            
            self.fontSize = newFontSize
            self.recalculate()

            self.text = self.parent.add_alignment_marker(self.loop, self.wire, self.uv_layer, self.document_scale, self.alignment_number_dictionary, self.position_dictionary, self.marker_list, self)[1].text

        def pointIntersects(self, point, upper_left_point, lower_right_point):
            # coordinate system is top left
            # 0,0 1,0
            # 0,1 1,1

            # text anchor is top left
            x_intersects = point[0] >= upper_left_point[0] and point[0] <= lower_right_point[0]
            y_intersects = point[1] >= upper_left_point[1] and point[1] <= lower_right_point[1]
        
            return x_intersects and y_intersects 

        def intersects(self,other):
            if other is self:
                return False
            
            other_pos = other.upper_left_point
            other_end = other.lower_right_point

            #top_left_intersects = self.pointIntersects((self.x,self.y), other_pos, other_end)
            lower_right_intersects = self.pointIntersects(self.lower_right_point, other_pos, other_end)
            lower_left_intersects = self.pointIntersects(self.lower_left_point, other_pos, other_end)
            upper_right_intersects = self.pointIntersects(self.upper_right_point, other_pos, other_end)

            #ignore top_left_intersects intersection, since we're not going to move the points
            return lower_right_intersects or upper_right_intersects or lower_left_intersects

    def add_text(self,x,y,fontSize,text):
        returnstring = ''

        returnstring += '<text x="'
        returnstring += str(x)
        returnstring += 'px" y="'
        returnstring += str(y)
        returnstring += 'px" style="font-family:\'Consolas\', \'Courier New\';font-size:'
        returnstring += str(fontSize)
        returnstring += 'px;">'
        returnstring += str(text)
        returnstring += '</text>\n'

        return returnstring

    def add_alignment_marker(self, loop, wire, uv_layer, document_scale, hashDictionary, positionDictionary, marker_list,markerInstance):
        wire_dir = mathutils.Vector((0,0));
        for l in loop.vert.link_edges:
            if (len(l.link_loops) > 0 and len(l.link_faces) == 1):
                this_dir = l.link_loops[0][uv_layer].uv - l.link_loops[0].link_loop_next[uv_layer].uv
                if (l.link_loops[0].vert == loop.vert):
                    wire_dir -= this_dir
                else:
                    wire_dir -= this_dir
        
        wire_dir.normalize()
        #wire_dir.y *= -1;
        wire_dir.xy = wire_dir.yx
        wire_dir *= 0.01;
        
        sew_color = mathutils.Color((1,0,0))
        color_hash = (hash(wire))

        alignment_number = -1
        if color_hash in hashDictionary:
            alignment_number = hashDictionary[color_hash]
        else:
            alignment_number = self.current_alignment_number
            self.current_alignment_number += 1
            hashDictionary[color_hash] = alignment_number
        
        color_hash /= 100000000.0
        color_hash *= 1345235.23523
        color_hash %= 1.0
        sew_color.hsv = color_hash, 1, 1
        sew_color_hex = "#%.2x%.2x%.2x" % (int(sew_color.r * 255), int(sew_color.g * 255), int(sew_color.b * 255))
        
        uv1 = loop[uv_layer].uv.copy();
        uv1.y = 1-uv1.y;

        x_position = (uv1.x + wire_dir.x) * document_scale
        y_position = (uv1.y + wire_dir.y) * document_scale
        x1_position = (uv1.x - wire_dir.x) * document_scale
        y1_position = (uv1.y - wire_dir.y) * document_scale
        
        # a line can start or end in the same spot
        # check to make sure we're not spawning
        # lines and duplicate numbers in the same spot
        lineHash = str(round(x_position)) + str(round(y_position)) + str(round(x1_position)) + str(round(y1_position))
        alternateLineHash = str(round(x1_position)) + str(round(y1_position)) + str(round(x_position)) + str(round(y_position))

        if(markerInstance is None):
            if lineHash in positionDictionary or alternateLineHash in positionDictionary:
                return (False,)

            positionDictionary[lineHash] = True
            positionDictionary[alternateLineHash] = True

        returnstring = '<path class="sewinguide" stroke="' + sew_color_hex + '" d="M '
        returnstring += str(x_position)
        returnstring += ','
        returnstring += str(y_position)
        returnstring += ' '

        returnstring += str(x1_position)
        returnstring += ','
        returnstring += str(y1_position)
        returnstring += ' '
        returnstring += '"/>\n'  

        fontSize = markerInstance.fontSize if markerInstance is not None else self.aligment_number_font_size

        returnstring += self.add_text(x1_position,y1_position,fontSize,alignment_number)
        
        result = markerInstance if markerInstance is not None else Export_Sewingpattern.Marker(self, 
                        x1_position,
                        y1_position,
                        self.aligment_number_font_size, 
                        returnstring, 
                        alignment_number,
                        loop, 
                        wire, 
                        uv_layer, 
                        document_scale, 
                        hashDictionary, 
                        positionDictionary, 
                        marker_list
                        )
        
        result.text = returnstring

        # make sure the none of the markers collide, and if they do resize them so they no longer collide
        i = 0
        while i < len(marker_list): 
            other = marker_list[i]
            if other.id is result.id:
                i += 1
                continue
            if (other.intersects(result)) and (other.fontSize > 1 or result.fontSize > 1):
                
                if other.fontSize > result.fontSize:
                    other.resize(other.fontSize - 1)
                elif other.fontSize < result.fontSize:
                    result.resize(result.fontSize - 1)
                else:
                    result.resize(result.fontSize - 1)
                    other.resize(other.fontSize - 1)
                
                continue
            i += 1

        return (True, result)
        
    def debug(self,text):
        self.report({'WARNING'}, text)

    def auto_detect_markers(self):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type="EDGE")
        bpy.ops.mesh.select_all(action='SELECT')

        obj = bpy.context.edit_object
        me = obj.data
        bm = bmesh.from_edit_mesh(me)

        bpy.ops.mesh.region_to_loop()

        bpy.ops.mesh.select_mode(type="VERT")

        boundary_vertices = [v for v in bm.verts if v.select]

        for v in boundary_vertices:
            intrest = 0
            for e in v.link_edges:
                if (len(e.link_faces) != 0):
                    intrest += 1;
            if intrest == 2:
                for l in v.link_edges:
                    if (len(l.link_faces) == 0):
                        l.seam = True
        
    
