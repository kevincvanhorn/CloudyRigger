# Installation:
Preferences > Add-ons > Install...
Enable: Object: Cloudy Rigger

# Use:
[Precondition: 
  - A driver with name py_head 
    & Limit Location constraint (Min/MaxX=-0.15/0.15, Min/MaxZ=-0.15/0.15, Affect Transform, Local Space)
]

Pose > Reset Cloudy Rig : removes all drivers and mappings
Pose > Map Left, Right, Top, Bot : for each selected bone, set it's corresponding key in the pose dictionary
Pose > Apply Mapping : set all selected bones to use the pose dictionary mappings
Pose > Reload Drivers : On load of a file, press this to reload the mapping function, otherwise it will not run

# Tips
N > Transform > Delete drivers for a bone to stop mapping and edit transform for any one of top/bot/left/right before mapping again

