#!/usr/bin/env python3
"""
Genereert een multi-color Bambu Studio compatibel 3MF bestand van de Nederlandse Kenteken Sleutelhanger.
Maakt gebruik van OpenSCAD om 4 afzonderlijke volumes te exporteren (Zwart, Geel, Blauw, Wit)
en bouwt een clean Bambu Studio 3MF assembly zonder vreemde machine/printer presets of G-code waarschuwingen.
"""

import os
import sys
import shutil
import zipfile
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def find_openscad():
    # macOS standaard paden en PATH controle
    paths = [
        "openscad",
        "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD",
        os.path.expanduser("~/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD")
    ]
    for p in paths:
        if shutil.which(p) or os.path.isfile(p):
            return p
    return None

def main():
    openscad = find_openscad()
    if not openscad:
        print("Fout: OpenSCAD niet gevonden! Installeer OpenSCAD of voeg het toe aan je PATH.")
        sys.exit(1)

    scad_file = os.path.join(SCRIPT_DIR, "Kenteken_Sleutelhanger.scad")
    if not os.path.isfile(scad_file):
        print(f"Fout: Kan {scad_file} niet vinden!")
        sys.exit(1)

    print(f"1. OpenSCAD gevonden: {openscad}")
    print("2. Exporteren van afzonderlijke kleuronderdelen via OpenSCAD...")

    wrapper_scad = os.path.join(SCRIPT_DIR, "_temp_wrap.scad")
    with open(wrapper_scad, "w") as f:
        f.write('''$fn = 60;
include <Kenteken_Sleutelhanger.scad>
part = "all";
if (part == "black") BlackParts();
else if (part == "yellow") YellowPart();
else if (part == "blue") BluePart();
else if (part == "white") WhiteParts();
''')

    parts = [
        ("Basis_Zwart", "black", 1, "#000000"),
        ("Plaat_Geel", "yellow", 2, "#FFCC00"),
        ("Vlak_Blauw", "blue", 3, "#003399"),
        ("Opdruk_Wit", "white", 4, "#FFFFFF")
    ]

    meshes = []
    try:
        for name, p_arg, extruder_id, color_hex in parts:
            stl_file = os.path.join(SCRIPT_DIR, f"_temp_{p_arg}.stl")
            cmd = [
                openscad,
                "-D", f'part="{p_arg}"',
                "-o", stl_file,
                "--export-format", "asciistl",
                wrapper_scad
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            verts = []
            tris = []
            vert_map = {}
            with open(stl_file, "r") as f:
                curr = []
                for line in f:
                    s = line.strip()
                    if s.startswith("vertex"):
                        coords = tuple(round(float(x), 5) for x in s.split()[1:])
                        # Centreer op printbed (x - 35.5, y - 7.5, z - 1.5)
                        c_coords = (round(coords[0] - 35.5, 5), round(coords[1] - 7.5, 5), round(coords[2] - 1.5, 5))
                        if c_coords not in vert_map:
                            vert_map[c_coords] = len(verts)
                            verts.append(c_coords)
                        curr.append(vert_map[c_coords])
                        if len(curr) == 3:
                            tris.append(tuple(curr))
                            curr = []

            meshes.append({
                "name": name,
                "extruder": extruder_id,
                "color": color_hex,
                "vertices": verts,
                "triangles": tris
            })
            print(f"   - {name} geëxporteerd: {len(verts)} hoekpunten, {len(tris)} driehoeken (Extruder {extruder_id})")
    finally:
        if os.path.exists(wrapper_scad):
            os.remove(wrapper_scad)
        for _, p_arg, _, _ in parts:
            p_stl = os.path.join(SCRIPT_DIR, f"_temp_{p_arg}.stl")
            if os.path.exists(p_stl):
                os.remove(p_stl)

    print("3. Samenstellen van Bambu Studio multi-part assembly...")

    # 3D/Objects/object_1.model
    obj_1_xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">',
        ' <metadata name="BambuStudio:3mfVersion">1</metadata>',
        ' <resources>'
    ]

    part_uuids = []
    for idx, m in enumerate(meshes):
        part_id = idx + 1
        u = f"0001000{idx}-81cb-4c03-9d28-80fed5dfa1dc"
        part_uuids.append((part_id, u, m))
        obj_1_xml.append(f'  <object id="{part_id}" p:UUID="{u}" type="model">')
        obj_1_xml.append('   <mesh>')
        obj_1_xml.append('    <vertices>')
        for v in m["vertices"]:
            obj_1_xml.append(f'     <vertex x="{v[0]:.5f}" y="{v[1]:.5f}" z="{v[2]:.5f}"/>')
        obj_1_xml.append('    </vertices>')
        obj_1_xml.append('    <triangles>')
        for t in m["triangles"]:
            obj_1_xml.append(f'     <triangle v1="{t[0]}" v2="{t[1]}" v3="{t[2]}"/>')
        obj_1_xml.append('    </triangles>')
        obj_1_xml.append('   </mesh>')
        obj_1_xml.append('  </object>')

    obj_1_xml.append(' </resources>')
    obj_1_xml.append('</model>')
    obj_1_str = '\n'.join(obj_1_xml)

    # 3D/3dmodel.model
    main_obj_id = 10
    main_obj_uuid = "00000001-61cb-4c03-9d28-80fed5dfa1dc"

    model_xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">',
        ' <metadata name="Application">BambuStudio-02.09.01.70</metadata>',
        ' <metadata name="BambuStudio:3mfVersion">1</metadata>',
        ' <metadata name="Title">Kenteken Sleutelhanger</metadata>',
        ' <resources>',
        f'  <object id="{main_obj_id}" p:UUID="{main_obj_uuid}" type="model">',
        '   <components>'
    ]

    for part_id, _, _ in part_uuids:
        comp_u = f"0001000{part_id-1}-b206-40ff-9872-83e8017abed1"
        model_xml.append(f'    <component p:path="/3D/Objects/object_1.model" objectid="{part_id}" p:UUID="{comp_u}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>')

    model_xml.append('   </components>')
    model_xml.append('  </object>')
    model_xml.append(' </resources>')
    model_xml.append(' <build p:UUID="2c7c17d8-22b5-4d84-8835-1976022ea369">')
    model_xml.append(f'  <item objectid="{main_obj_id}" p:UUID="0000000c-b1ec-4553-aec9-835e5b724bb4" transform="1 0 0 0 1 0 0 0 1 128 128 1.5" printable="1"/>')
    model_xml.append(' </build>')
    model_xml.append('</model>')
    model_str = '\n'.join(model_xml)

    # Metadata/model_settings.config
    total_facets = sum(len(m["triangles"]) for m in meshes)
    config_xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<config>',
        f'  <object id="{main_obj_id}">',
        '    <metadata key="name" value="Kenteken Sleutelhanger"/>',
        '    <metadata key="extruder" value="1"/>',
        f'    <metadata face_count="{total_facets}"/>'
    ]

    for part_id, _, m in part_uuids:
        part_u = f"abb07f8{part_id}-4c2f-4d94-8ef8-0326f4636268"
        config_xml.append(f'    <part id="{part_id}" subtype="normal_part" uuid="{part_u}">')
        config_xml.append(f'      <metadata key="name" value="{m["name"]}"/>')
        config_xml.append('      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>')
        config_xml.append('      <metadata key="source_file" value="Kenteken_Sleutelhanger.3mf"/>')
        config_xml.append(f'      <metadata key="source_object_id" value="{part_id}"/>')
        config_xml.append(f'      <metadata key="source_volume_id" value="{part_id}"/>')
        config_xml.append('      <metadata key="source_offset_x" value="35.5"/>')
        config_xml.append('      <metadata key="source_offset_y" value="7.5"/>')
        config_xml.append('      <metadata key="source_offset_z" value="1.5"/>')
        config_xml.append(f'      <metadata key="extruder" value="{m["extruder"]}"/>')
        config_xml.append(f'      <mesh_stat face_count="{len(m["triangles"])}" edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>')
        config_xml.append('    </part>')

    config_xml.append('  </object>')
    config_xml.append('  <plate>')
    config_xml.append('    <metadata key="plater_id" value="1"/>')
    config_xml.append('    <metadata key="plater_name" value=""/>')
    config_xml.append('    <metadata key="locked" value="false"/>')
    config_xml.append('    <metadata key="filament_map_mode" value="Auto For Flush"/>')
    config_xml.append('    <metadata key="filament_maps" value="1 2 3 4"/>')
    config_xml.append('    <metadata key="filament_volume_maps" value="0 0 0 0"/>')
    config_xml.append('    <metadata key="thumbnail_file" value="Metadata/plate_1.png"/>')
    config_xml.append('    <metadata key="top_file" value="Metadata/top_1.png"/>')
    config_xml.append('    <metadata key="pick_file" value="Metadata/pick_1.png"/>')
    config_xml.append('    <model_instance>')
    config_xml.append(f'      <metadata key="object_id" value="{main_obj_id}"/>')
    config_xml.append('      <metadata key="instance_id" value="0"/>')
    config_xml.append('      <metadata key="identify_id" value="71"/>')
    config_xml.append('    </model_instance>')
    config_xml.append('  </plate>')
    config_xml.append('  <assemble>')
    config_xml.append(f'   <assemble_item object_id="{main_obj_id}" instance_id="0" transform="1 0 0 0 1 0 0 0 1 128 128 1.5" offset="0 0 0" />')
    for part_id, _, _ in part_uuids:
        config_xml.append(f'   <assemble_item object_id="{main_obj_id}" volume_id="{part_id-1}" transform="1 0 0 0 1 0 0 0 1 0 0 0" />')
    config_xml.append('  </assemble>')
    config_xml.append('</config>')
    config_str = '\n'.join(config_xml)

    # Inpakken
    out_3mf = os.path.join(SCRIPT_DIR, "Kenteken_Sleutelhanger.3mf")
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

    with zipfile.ZipFile(out_3mf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model_str)
        z.writestr("3D/_rels/3dmodel.model.rels", rels_model)
        z.writestr("3D/Objects/object_1.model", obj_1_str)
        z.writestr("Metadata/model_settings.config", config_str)

    print(f"\nKlaar! Multi-volume 3MF succesvol opgeslagen als:\n-> {out_3mf}")

if __name__ == "__main__":
    main()
