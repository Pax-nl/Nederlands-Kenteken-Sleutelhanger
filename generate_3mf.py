#!/usr/bin/env python3
"""
Nederlands Kenteken Sleutelhanger - 3MF Generator
Genereert een Bambu Studio / AMS-compatibel multi-color .3mf bestand
rechtstreeks vanuit het OpenSCAD model, zonder slice gcode.
"""

import os
import sys
import zipfile
import subprocess
import xml.etree.ElementTree as ET

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCAD_FILE = os.path.join(SCRIPT_DIR, "Kenteken_Sleutelhanger.scad")
OUTPUT_3MF = os.path.join(SCRIPT_DIR, "Kenteken_Sleutelhanger.3mf")
TEMP_3MF = os.path.join(SCRIPT_DIR, "temp_openscad.3mf")

# Check for OpenSCAD executable
OPENSCAD_BIN = "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
if not os.path.exists(OPENSCAD_BIN):
    # Try system PATH
    import shutil
    OPENSCAD_BIN = shutil.which("openscad")

if not OPENSCAD_BIN or not os.path.exists(OPENSCAD_BIN):
    print("Fout: OpenSCAD niet gevonden! Installeer OpenSCAD of zet het in /Applications.")
    sys.exit(1)

print(f"1. Compileren van 3D model met OpenSCAD ({OPENSCAD_BIN})...")
cmd = [OPENSCAD_BIN, "-o", TEMP_3MF]
if len(sys.argv) > 1:
    # Pass extra OpenSCAD parameters (bijv. -D 'kenteken_tekst="12-AB-34"')
    cmd.extend(sys.argv[1:])
cmd.append(SCAD_FILE)

subprocess.run(cmd, check=True)

print("2. Verwerken van multi-color geometrie naar Bambu Studio paint_color structuur...")
with zipfile.ZipFile(TEMP_3MF, "r") as z:
    model_xml_raw = z.read("3D/3dmodel.model")

root = ET.fromstring(model_xml_raw)
ns = {'m': 'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}

obj = root.find('.//m:object', ns)
mesh = obj.find('m:mesh', ns)

vertices = []
for v in mesh.findall('m:vertices/m:vertex', ns):
    vertices.append((float(v.attrib['x']), float(v.attrib['y']), float(v.attrib['z'])))

# Centreer coördinaten voor Bambu Studio (x - 35.5, y - 7.5, z - 1.5)
centered_vertices = [(x - 35.5, y - 7.5, z - 1.5) for (x, y, z) in vertices]

triangles = []
paint_map = {
    '1': '4',   # Filament 1: Zwart (basis, buitenrand, tekst)
    '2': '0C',  # Filament 2: Geel (kentekenvlak)
    '3': '8',   # Filament 3: Blauw (Europees vlak)
    '4': '1C'   # Filament 4: Wit (sleutelring, landcode)
}

for t in mesh.findall('m:triangles/m:triangle', ns):
    v1 = t.attrib['v1']
    v2 = t.attrib['v2']
    v3 = t.attrib['v3']
    p1 = t.attrib.get('p1', '1')
    paint_color = paint_map.get(p1, '4')
    triangles.append((v1, v2, v3, paint_color))

print(f"   Vertices: {len(centered_vertices)}, Driehoeken: {len(triangles)}")

# Bouw 3D/Objects/object_1.model
obj_1_xml = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">',
    ' <metadata name="BambuStudio:3mfVersion">1</metadata>',
    ' <resources>',
    '  <object id="1" p:UUID="00010000-81cb-4c03-9d28-80fed5dfa1dc" type="model">',
    '   <mesh>',
    '    <vertices>'
]
for x, y, z in centered_vertices:
    obj_1_xml.append(f'     <vertex x="{x:.7f}" y="{y:.7f}" z="{z:.7f}"/>')
obj_1_xml.append('    </vertices>')
obj_1_xml.append('    <triangles>')
for v1, v2, v3, pc in triangles:
    obj_1_xml.append(f'     <triangle v1="{v1}" v2="{v2}" v3="{v3}" paint_color="{pc}"/>')
obj_1_xml.append('    </triangles>')
obj_1_xml.append('   </mesh>')
obj_1_xml.append('  </object>')
obj_1_xml.append(' </resources>')
obj_1_xml.append('</model>')

new_obj_1_str = '\n'.join(obj_1_xml)

# Hoofdmodel 3D/3dmodel.model
model_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">
 <metadata name="Application">BambuStudio-02.09.01.70</metadata>
 <metadata name="BambuStudio:3mfVersion">1</metadata>
 <metadata name="Title">Kenteken Sleutelhanger</metadata>
 <resources>
  <object id="2" p:UUID="00000001-61cb-4c03-9d28-80fed5dfa1dc" type="model">
   <components>
    <component p:path="/3D/Objects/object_1.model" objectid="1" p:UUID="00010000-b206-40ff-9872-83e8017abed1" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>
   </components>
  </object>
 </resources>
 <build p:UUID="2c7c17d8-22b5-4d84-8835-1976022ea369">
  <item objectid="2" p:UUID="00000002-b1ec-4553-aec9-835e5b724bb4" transform="1 0 0 0 1 0 0 0 1 128 128 1.5" printable="1"/>
 </build>
</model>'''

# Metadata configuratie
model_settings = f'''<?xml version="1.0" encoding="UTF-8"?>
<config>
  <object id="2">
    <metadata key="name" value="Kenteken Sleutelhanger"/>
    <metadata key="extruder" value="1"/>
    <metadata face_count="{len(triangles)}"/>
    <part id="1" subtype="normal_part" uuid="abb07f89-4c2f-4d94-8ef8-0326f4636268">
      <metadata key="name" value="Kenteken Sleutelhanger"/>
      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
      <metadata key="source_file" value="Kenteken_Sleutelhanger.3mf"/>
      <metadata key="source_object_id" value="0"/>
      <metadata key="source_volume_id" value="0"/>
      <metadata key="source_offset_x" value="35.5"/>
      <metadata key="source_offset_y" value="7.5"/>
      <metadata key="source_offset_z" value="1.5"/>
      <metadata key="extruder" value="1"/>
      <mesh_stat face_count="{len(triangles)}" edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>
    </part>
  </object>
  <plate>
    <metadata key="plater_id" value="1"/>
    <metadata key="plater_name" value=""/>
    <metadata key="locked" value="false"/>
    <metadata key="filament_map_mode" value="Auto For Flush"/>
    <metadata key="thumbnail_file" value="Metadata/plate_1.png"/>
    <metadata key="top_file" value="Metadata/top_1.png"/>
    <metadata key="pick_file" value="Metadata/pick_1.png"/>
    <model_instance>
      <metadata key="object_id" value="2"/>
      <metadata key="instance_id" value="0"/>
      <metadata key="identify_id" value="71"/>
    </model_instance>
  </plate>
  <assemble>
   <assemble_item object_id="2" instance_id="0" transform="1 0 0 0 1 0 0 0 1 128 128 1.5" offset="0 0 0" />
   <assemble_item object_id="2" volume_id="0" transform="1 0 0 0 1 0 0 0 1 0 0 0" />
  </assemble>
</config>'''

project_settings = '''{
    "filament_colour": [
        "#111111",
        "#FFCC00",
        "#003399",
        "#FFFFFF"
    ],
    "filament_type": [
        "PLA",
        "PLA",
        "PLA",
        "PLA"
    ],
    "filament_vendor": [
        "Generic",
        "Generic",
        "Generic",
        "Generic"
    ]
}'''

content_types = '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
 <Default Extension="png" ContentType="image/png"/>
 <Default Extension="config" ContentType="application/octet-stream"/>
</Types>'''

rels = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>'''

rels_model = '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/Objects/object_1.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>'''

print("3. Inpakken naar clean Bambu Studio 3MF...")
with zipfile.ZipFile(OUTPUT_3MF, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", content_types)
    z.writestr("_rels/.rels", rels)
    z.writestr("3D/3dmodel.model", model_xml)
    z.writestr("3D/_rels/3dmodel.model.rels", rels_model)
    z.writestr("3D/Objects/object_1.model", new_obj_1_str)
    z.writestr("Metadata/model_settings.config", model_settings)
    z.writestr("Metadata/project_settings.config", project_settings)

if os.path.exists(TEMP_3MF):
    os.remove(TEMP_3MF)

print(f"Klaar! Bestand succesvol opgeslagen als: {OUTPUT_3MF}")
