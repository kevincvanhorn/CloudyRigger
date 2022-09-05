bl_info = {
    "name": "Cloudy Rigger",
    "blender": (3, 2, 2),
    "category": "Object",
}


import bpy
from mathutils import Matrix
from bpy.types import Operator
from bpy.app.handlers import persistent


def update_dependencies(ob):
    def updateExp(d):
        # https://blender.stackexchange.com/questions/118350/how-to-update-the-dependencies-of-a-driver-via-python-script
        d.driver.expression += " "
        d.driver.expression = d.driver.expression[:-1]
    try:
        drivers = ob.animation_data.drivers
        for d in drivers:
            updateExp(d)
    except AttributeError:
        return

# =================================================

def get_selected_bones(): # selected bones in pose mode names = [x.name for x in selected_bones]
    return bpy.context.selected_pose_bones # returns a PoseBone # https://docs.blender.org/api/current/bpy.types.PoseBone.html

def clear_pose():
    for bone in bpy.data.objects['Armature'].pose.bones:
        bone.matrix_basis = Matrix()

# ddict has 5 elements for each bone:
BASIS = 0; LEFT = 1; TOP = 2; RIGHT =3; BOT = 4
JOYSTICK = "py_head" # what bone is the joystick

#ddict = {}

# system: remove and reset ddict of bones and their transforms per corner.
def initialize():
    print('\n\n')
    mybone = None; reset= True
    
    # Case: calling this multiple times
    #if len(bpy.data.scenes['Scene']['ddict']) > 0:
    #    bpy.data.scenes['Scene']['ddict'].clear()
        
    # Initialize and Populate dict from rig bones
    bpy.data.scenes['Scene']['ddict'] = {}#{'bone':[{},{},{}]}
    for bone in bpy.data.objects['Armature'].pose.bones:
        bone.matrix_basis = Matrix() # reset to binding pose
        bpy.data.scenes['Scene']['ddict'][bone.name] = [
                {'loc':bone.location, 'rot':bone.rotation_quaternion, 'scale':bone.scale},
                {'loc':bone.location, 'rot':bone.rotation_quaternion, 'scale':bone.scale},
                {'loc':bone.location, 'rot':bone.rotation_quaternion, 'scale':bone.scale},
                {'loc':bone.location, 'rot':bone.rotation_quaternion, 'scale':bone.scale},
                {'loc':bone.location, 'rot':bone.rotation_quaternion, 'scale':bone.scale},
            ]

# user: reset mappings
def reset_mapping():
    initialize() # reset ddict object
    print('Initializing scene with new dict')
    
    for bone in bpy.data.objects['Armature'].pose.bones:
        bone.driver_remove('location')
        bone.driver_remove('rotation_quaternion')
        bone.driver_remove('scale')

def try_load():
    '''
    This was in registration of script, but w/o a callback this must be done on execution 
    '''
    try:
        if len(bpy.data.scenes['Scene']['ddict']) >= 0:
            print('Found existing dict')
            #ddict = bpy.data.scenes['Scene']['ddict'].to_dict()
    except: # key not found
        print('No cloudy rig registered to this file.')
        initialize()

def set_mapping(dir):
    try_load();
    if len(bpy.data.scenes['Scene']['ddict']) == 0:
        reset_mapping()
    
    for bone in get_selected_bones():#bpy.data.objects['Armature'].pose.bones:
        if not bone.name in bpy.data.scenes['Scene']['ddict'] or len(bpy.data.scenes['Scene']['ddict'][bone.name]) != 5:
            print('Missing bone, must reset mapping.') # TODO allow for adding new bones without wiping mapping
            bpy.data.scenes['Scene']['ddict'].clear()
            break;
        print('loc=', bone.location)
        bpy.data.scenes['Scene']['ddict'][bone.name][dir]['loc'] = bone.location
        bpy.data.scenes['Scene']['ddict'][bone.name][dir]['rot'] = bone.rotation_quaternion
        bpy.data.scenes['Scene']['ddict'][bone.name][dir]['scale'] = bone.scale
    #calculate_drivers() # reset selected drivers anytime we map selected

def apply_mappings():
    calculate_drivers() # reset selected drivers anytime we map selected   

## DRIVER HANDLERS:

def cloudy_driver(bone, prop, index):
    pprop = 'loc'
    if prop == 'scale': pprop = 'scale'
    elif prop == 'rotation_quaternion': pprop = 'rot'
    d = 0.15 # the side length of the joystick assumed center of zero and contrained w/ limit_location bone constraint, affect trans, local space
    lerper = bpy.data.objects['Armature'].pose.bones['py_head']
    dir = 0;
    
    # x,y of the driver with middle as 0,0 and extents as [d]
    x = lerper.location.x
    y = lerper.location.z
    
    def dval(dir):
        return bpy.data.scenes['Scene']['ddict'][bone][dir][pprop][index]
    
    # Interpolate loc / scale Properties
    if pprop == 'loc' or pprop == 'scale' or pprop == 'rot': # for X prop
        vals=[]
        
        id = 0 # identity, zero for all but w of quaternion
        if pprop == 'scale' or (pprop == 'rot' and index == 0):
            id = 1
        
        if x <=0:
            if y>= 0: # top left
                vals =[dval(TOP), dval(LEFT), id]
            else: #bot left
                vals = [dval(BOT),dval(LEFT), id]
        else:
            if y >= 0: # top right
                vals =[dval(TOP),dval(RIGHT), id]
            else: # bottom right
                vals = [dval(BOT), dval(RIGHT), id]
                
        # barycentric_interpolation, finding the area of each corner triangle
        x= abs(x); y = abs(y)
        w1 = y/d; w2 = x/d
        
        # Clamp x & y to not reach beyond the right triangles from the centerpoint (0,0)->(d,0) or (0,d)
        # Comment out to get rid of diagonal clamping
        '''
        if w1+w2 > 1:
            # line from point a (0,d) to b (d,0)
            dot = d*x - d*(y-d)
            llen = d*d + d*d
            x = (dot*d)/llen
            y = d+(-dot*d)/llen
            w1 = y/d; w2 = x/d
        ''' 
        # rotation_quaternion default (1, 0, 0, 0)
        # Average of quaternions that are close is approximately correct
        
        #print(prop, 'INDEX: ', index)
        #print('(%d)*%d + (%d)*%d (%d)*%d'  % (vals[0],w1,vals[1],w2,vals[2],(1-w1-w2)))
            
        return vals[0]*w1 + vals[1]*w2 + vals[2]*(1 - w1 - w2)
        
    return 0

def add_driver(bone, prop, index): #DriverVariable
    d = bone.driver_add(prop,index).driver # x
    '''
    _x = d.variables.new()
    _x.name = 'x'
    # bpy.context.object.animation_data.drivers[0].driver.variables[0].type
    _x.type = 'TRANSFORMS'
    _x.targets[0].id = bpy.data.objects['Armature']#.pose.bones[JOYSTICK].id_data
    _x.targets[0].bone_target = JOYSTICK
    _x.targets[0].transform_space = 'LOCAL_SPACE'#'LOCAL_SPACE'
    _x.targets[0].transform_type = 'LOC_X'
    
    _y = d.variables.new()
    _y.name = 'y'
    _y.type = 'TRANSFORMS'
    _y.targets[0].id = bpy.data.objects['Armature']#.pose.bones[JOYSTICK].id_data
    _y.targets[0].bone_target = JOYSTICK
    _y.targets[0].transform_space = 'LOCAL_SPACE'
    _y.targets[0].transform_type = 'LOC_Z'
    '''
    #d.expression = '(lambda bone, prop, index : ( pprop := \'loc\' if prop == \'location\' else \'scale\' if prop == \'scale\' else \'rotation_quaternion\', dval := lambda dir : bpy.data.scenes[\'Scene\'][\'ddict\'][bone][dir][pprop][index], id = 1 if (pprop == \'scale\' or (pprop == \'rot\' and index == 0)) else 0, vals := [dval(TOP), dval(LEFT), id] if (x <=0 and y>=0) else [dval(BOT),dval(LEFT), id] if (x <=0) else [dval(TOP),dval(RIGHT), id] if(y>=0) else [dval(BOT), dval(RIGHT), id], w1 := abs(y)/d, w2 := abs(x)/d, vals[0]*w1 + vals[1]*w2 + vals[2]*(1 - w1 - w2))[-1])(%s, %s, %d)' % (bone, prop, index);
    #d.expression = '(lambda b,p,i:(r:=\'loc\'if p==\'location\' else \'scale\' if p==\'scale\' else \'rotation_quaternion\',dval:=lambda d: bpy.data.scenes[\'Scene\'][\'ddict\'][b][d][r][i], id = 1 if (r==\'scale\' or (r==\'rot\' and i==0)) else 0, vals := [dval(TOP), dval(LEFT), id] if (x <=0 and y>=0) else [dval(BOT),dval(LEFT), id] if (x <=0) else [dval(TOP),dval(RIGHT), id] if(y>=0) else [dval(BOT), dval(RIGHT), id], w1 := abs(y)/d, w2 := abs(x)/d, vals[0]*w1 + vals[1]*w2 + vals[2]*(1 - w1 - w2))[-1])(%s, %s, %d)' % (bone, prop, index);
    #d.expression = '''(lambda bone, prop, index : 
    #    (
    #        pprop := \'loc\' if prop == \'location\' else \'scale\' if prop == \'scale\' else \'rotation_quaternion\',
    #        dval := lambda dir : bpy.data.scenes[\'Scene\'][\'ddict\'][bone][dir][pprop][index],
    #        id = 1 if (pprop == \'scale\' or (pprop == \'rot\' and index == 0)) else 0,
    #        vals := [dval(TOP), dval(LEFT), id] if (x <=0 and y>=0) else [dval(BOT),dval(LEFT), id] if (x <=0)
    #            else [dval(TOP),dval(RIGHT), id] if(y>=0) else [dval(BOT), dval(RIGHT), id],
    #        w1 := abs(y)/d,
    #        w2 := abs(x)/d,
    #        vals[0]*w1 + vals[1]*w2 + vals[2]*(1 - w1 - w2)
    #    )[-1]
    #)(%s, %s, %d)''' % (bone, prop, index);

    # TO NOT use the in-place version uncomment this line and comment the rest above
    d.expression = 'bpy.app.driver_namespace[\'cloudy_driver\'](\'%s\', \'%s\', %d)' % (bone.name, prop, index)

@persistent
def load_handler(dummy):
    bpy.app.driver_namespace['cloudy_driver'] = cloudy_driver

def calculate_drivers():
    #global ddict
    for bone in get_selected_bones():
        # remove existing drivers
        bone.driver_remove('location')
        bone.driver_remove('rotation_quaternion')
        bone.driver_remove('scale')
        
        [add_driver(bone, 'location',x) for x in range(3)]
        # NOTE: May need to set posebone property to Quaternion (WXYZ)
        [add_driver(bone, 'rotation_quaternion',x) for x in range(4)]
        [add_driver(bone, 'scale', x) for x in range(3)]
    
# working, script testing entry point
def run():
    #global ddict
    if len(bpy.data.scenes['Scene']['ddict']) <0 :
        reset_mapping()
        
# BLENDER UI =============================================================================
        
# Operator = function to call from menu
class ResetMapping(bpy.types.Operator):
    """Reinitialize cloudy rig mapping"""           # Use this as a tooltip for menu items and buttons.
    bl_idname = "cloudy.resetmapping"     # Unique identifier for buttons and menu items to reference.
    bl_label = "Reset Cloudy Rig"            # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.

    def execute(self, context):        # execute() is called when running the operator.
        reset_mapping();
        return {'FINISHED'}            # Lets Blender know the operator finished successfully.

class MapLeft(bpy.types.Operator):
    """ Map bones to the left joystick position."""           # Use this as a tooltip for menu items and buttons.
    bl_idname = "cloudy.mapleft"     # Unique identifier for buttons and menu items to reference.
    bl_label = "Map Left"            # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.
    def execute(self, context):        # execute() is called when running the operator.
        set_mapping(LEFT);
        return {'FINISHED'}            # Lets Blender know the operator finished successfully.
class MapRight(bpy.types.Operator):
    """ Map bones to the right joystick position."""           # Use this as a tooltip for menu items and buttons.
    bl_idname = "cloudy.mapright"     # Unique identifier for buttons and menu items to reference.
    bl_label = "Map Right"            # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.
    def execute(self, context):        # execute() is called when running the operator.
        set_mapping(RIGHT);
        return {'FINISHED'}            # Lets Blender know the operator finished successfully.
class MapTop(bpy.types.Operator):
    """ Map bones to the top joystick position."""           # Use this as a tooltip for menu items and buttons.
    bl_idname = "cloudy.maptop"     # Unique identifier for buttons and menu items to reference.
    bl_label = "Map Top"            # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.
    def execute(self, context):        # execute() is called when running the operator.
        set_mapping(TOP);
        return {'FINISHED'}            # Lets Blender know the operator finished successfully.
class MapBot(bpy.types.Operator):
    """ Map bones to the bottom joystick position."""           # Use this as a tooltip for menu items and buttons.
    bl_idname = "cloudy.mapbot"     # Unique identifier for buttons and menu items to reference.
    bl_label = "Map Bottom"            # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.
    def execute(self, context):        # execute() is called when running the operator.
        set_mapping(BOT);
        return {'FINISHED'}            # Lets Blender know the operator finished successfully.

class ApplyMapping(bpy.types.Operator):
    """ Applies all mappings to selected bone."""           # Use this as a tooltip for menu items and buttons.
    bl_idname = "cloudy.apply"     # Unique identifier for buttons and menu items to reference.
    bl_label = "Apply Mapping"            # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.
    def execute(self, context):        # execute() is called when running the operator.
        apply_mappings()
        return {'FINISHED'}            # Lets Blender know the operator finished successfully.

class ReloadDrivers(bpy.types.Operator):
    """ Applies all mappings to selected bone."""           # Use this as a tooltip for menu items and buttons.
    bl_idname = "cloudy.reload"     # Unique identifier for buttons and menu items to reference.
    bl_label = "Reload Drivers"            # Display name in the interface.
    bl_options = {'REGISTER', 'UNDO'}  # Enable undo for the operator.
    def execute(self, context):        # execute() is called when running the operator.
        for ob in bpy.data.objects:
            update_dependencies(ob)
        return {'FINISHED'}            # Lets Blender know the operator finished successfully.


# event to draw the menu that displays all of our custom functions/operators
def draw_menu(self, context):
    layout = self.layout
    layout.separator()
    layout.operator(ResetMapping.bl_idname)
    layout.operator(MapLeft.bl_idname)
    layout.operator(MapRight.bl_idname)
    layout.operator(MapTop.bl_idname)
    layout.operator(MapBot.bl_idname)
    layout.operator(ReloadDrivers.bl_idname)
    layout.operator(ApplyMapping.bl_idname)

# PLUGIN ENTRY ==================================================================================

def register():
    #global ddict
    # this func is NOT CALLED when a new file is created
    # Load from or to scene file
    #print('Initializing scene with new dict')
    #bpy.data.scenes['Scene']['ddict'] = ddict # C.scene['ddict']

    # Register Operator (function) classes and add the menu to the "Pose Mode" Pose dropdown
    bpy.utils.register_class(ResetMapping)
    bpy.utils.register_class(MapLeft)
    bpy.utils.register_class(MapRight)
    bpy.utils.register_class(MapTop)
    bpy.utils.register_class(MapBot)
    bpy.utils.register_class(ApplyMapping)
    bpy.utils.register_class(ReloadDrivers)
    bpy.types.VIEW3D_MT_pose.append(draw_menu)
    
    load_handler(None)
    bpy.app.handlers.load_post.append(load_handler)

def unregister():
    #try:
    #    bpy.data.scenes['Scene']['ddict'].clear()
    #    del bpy.data.scenes['Scene']['ddict']
    #except:
    #    print('no ddict found on unregister.')
    
    bpy.utils.unregister_class(ResetMapping)
    bpy.utils.unregister_class(MapLeft)
    bpy.utils.unregister_class(MapRight)
    bpy.utils.unregister_class(MapTop)
    bpy.utils.unregister_class(MapBot)
    bpy.utils.unregister_class(ApplyMapping)
    bpy.utils.unregister_class(ReloadDrivers)
    bpy.types.VIEW3D_MT_pose.remove(draw_menu)
    
    bpy.app.handlers.load_post.remove(load_handler)


# ONLY CALLED when running script manually:
if __name__ == "__main__":
    register()
    #run()
    
    #for ob in bpy.data.objects:
    #    update_dependencies(ob)
    
    #import inspect -> inspect.getmembers(object)
    #https://blenderartists.org/t/correct-way-to-store-an-array-in-a-custom-property/1383075/18
    #import addon_utils > print(addon_utils.paths())
