# Blender Seams to Sewing Pattern Remastered

This is a remastered version of the Original Blender Seams To Sewing Pattern.

This is an add-on for Blender that assists with setting up 2D sewing patterns from 3D models, for cloth simulation and real-life sewing.

![](https://blenderartists.org/uploads/default/optimized/4X/3/7/9/379d4a76a9022a7ff338773500784e22500dd8f6_2_690x207.jpeg)\
[![](https://img.youtube.com/vi/EZr__pTxsKk/mqdefault.jpg)\
▶ Quick guide on youtube](https://www.youtube.com/watch?v=EZr__pTxsKk)

# Installation
Download from the Releases section on Github

In Blender, go to `Edit > ⚙️ Preferences > Install..` and select the zip file you just downloaded.\
Enable the add-on in the list.

# Brief Overview:
![](https://gitlab.com/thomaskole/blender-seams-to-sewing-pattern/-/wikis/uploads/2364f88e60b43cf0cc44309c2e4f15be/triceratops.gif)

`Object > Seams to Sewing Pattern > Seams to Sewing Pattern`\
turns your mesh into a sewing patten based on it's UV layout.

`Object > Seams to Sewing Pattern > Quick Clothsim`\
Applies some basic cloth sim options to your Object

`Object > Seams to Sewing Pattern > Export Sewing Pattern (.svg)`\
Exports your sewing pattern to a .SVG file for printing and sewing in real life.

`Edge > Clean up Knife Cut`\
Clean up selected edges after you used the knife tool on a mesh

# Reporting Issues
Something wrong? Please file a bug report here on github!

Do not reach out to the original creator if you're using this software, only reach out
to them if you're using the orginal software!

# Troubleshooting

**I'm getting a python error**\
That's bad, please let me know the error and how you triggered it.

**After unfolding, there's some weird long triangles /strips flying out**\
Most likely some non-manifold geometry, overlapping vertices, or bad normals.\
Disable the remesh option and see where it goes wrong in your mesh / UV'seams

**My mesh is imploding on itself during clothsim**\
Yeah, clothsim... Try balancing the "pressure" and "sewing force".\
It can help to keyframe the "pressure" to something very high on frame 1 and decrease over time.

# license

GPL V3+ (Previously GPL V2+):\
[GPL-license.txt](./GPL-license.txt)

# Sustainability and Ethics 🌱

The production of natural textiles often involve overuse of water, fertilizers and perticides.\
Synthetic textiles are a large, often overlooked source of plastic pollution.\
The textile industry is often associated with unethical work conditions.

If you wish to use this add-on for real-life sewing purposes, I ask of you to use only sustainable / second-hand fabrics, and fair labour.

See also:\
[Sustainability-and-Ethics-notice.txt](./Sustainability-and-Ethics-notice.txt)

# Known Issues
- UV's are messed up after Remesh

# Credits
This projects includes code from MeasureIt by MeasureIt by the Blender Community, licensed under GPLv3+
See: https://extensions.blender.org/add-ons/measureit