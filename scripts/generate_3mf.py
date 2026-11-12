#!/usr/bin/env python3
"""
Genereert een universeel compatibel multi-color 3MF bestand van de Nederlandse Kenteken Sleutelhanger.
Maakt gebruik van de officiële 3MF Material & Production Extensions (colorgroup & multi-object).
Compatibel met Bambu Studio, OrcaSlicer, PrusaSlicer en andere moderne 3D slicers
zonder foutmeldingen, zonder vreemde printer presets en zonder waarschuwingen.
"""

import os
import sys
import shutil
import zipfile
import subprocess
import uuid

# Paden bepalen
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

def find_openscad():
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

    scad_file = os.path.join(REPO_ROOT, "Kenteken_Sleutelhanger.scad")
    if not os.path.isfile(scad_file):
        print(f"Fout: Kan {scad_file} niet vinden!")
        sys.exit(1)

    print(f"1. OpenSCAD gevonden: {openscad}")
    print("2. Exporteren van afzonderlijke kleuronderdelen via OpenSCAD...")

    wrapper_scad = os.path.join(SCRIPT_DIR, "_temp_wrap.scad")
    with open(wrapper_scad, "w") as f:
        f.write(f'''$fn = 60;
include <{scad_file}>
part = "all";
if (part == "black") BlackParts();
else if (part == "yellow") YellowPart();
else if (part == "blue") BluePart();
else if (part == "white") WhiteParts();
''')

    parts = [
        ("Basis_Zwart", "black", "#111111FF", 1),
        ("Plaat_Geel", "yellow", "#FFCC00FF", 2),
        ("Vlak_Blauw", "blue", "#003399FF", 3),
        ("Opdruk_Wit", "white", "#FFFFFFFF", 4)
    ]

    meshes = []
    try:
        for name, p_arg, color_hex, ext_id in parts:
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
                        if coords not in vert_map:
                            vert_map[coords] = len(verts)
                            verts.append(coords)
                        curr.append(vert_map[coords])
                        if len(curr) == 3:
                            tris.append(tuple(curr))
                            curr = []

            meshes.append({
                "name": name,
                "color": color_hex,
                "extruder": ext_id,
                "vertices": verts,
                "triangles": tris
            })
            print(f"   - {name}: {len(verts)} hoekpunten, {len(tris)} driehoeken (Kleur {color_hex})")
    finally:
        if os.path.exists(wrapper_scad):
            os.remove(wrapper_scad)
        for _, p_arg, _, _ in parts:
            p_stl = os.path.join(SCRIPT_DIR, f"_temp_{p_arg}.stl")
            if os.path.exists(p_stl):
                os.remove(p_stl)

    print("3. Bouwen van universeel multi-color 3MF model...")

    # We construeren een officiële 3MF met material extension (m:colorgroup)
    # Elke part is een eigen <object> met pid en pindex, en opgenomen in <build>
    # Dit werkt out-of-the-box in Bambu Studio / OrcaSlicer / PrusaSlicer zonder errors.
    xml_lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" unit="millimeter" xml:lang="en-US" xmlns:m="http://schemas.microsoft.com/3dmanufacturing/material/2015/02" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06">',
        '  <metadata name="Title">Kenteken Sleutelhanger</metadata>',
        '  <resources>'
    ]

    # Kleurgroepen toevoegen
    # colorgroup id's: 10, 20, 30, 40
    for idx, m in enumerate(meshes):
        cg_id = (idx + 1) * 10
        xml_lines.append(f'    <m:colorgroup id="{cg_id}">')
        xml_lines.append(f'      <m:color color="{m["color"]}"/>')
        xml_lines.append('    </m:colorgroup>')

    # Objecten toevoegen
    build_items = []
    for idx, m in enumerate(meshes):
        obj_id = idx + 1
        cg_id = (idx + 1) * 10
        obj_uuid = str(uuid.uuid4())
        item_uuid = str(uuid.uuid4())
        build_items.append((obj_id, item_uuid))

        xml_lines.append(f'    <object id="{obj_id}" name="{m["name"]}" type="model" p:UUID="{obj_uuid}" pid="{cg_id}" pindex="0">')
        xml_lines.append('      <mesh>')
        xml_lines.append('        <vertices>')
        for v in m["vertices"]:
            xml_lines.append(f'          <vertex x="{v[0]:.5f}" y="{v[1]:.5f}" z="{v[2]:.5f}"/>')
        xml_lines.append('        </vertices>')
        xml_lines.append('        <triangles>')
        for t in m["triangles"]:
            xml_lines.append(f'          <triangle v1="{t[0]}" v2="{t[1]}" v3="{t[2]}"/>')
        xml_lines.append('        </triangles>')
        xml_lines.append('      </mesh>')
        xml_lines.append('    </object>')

    xml_lines.append('  </resources>')
    xml_lines.append(f'  <build p:UUID="{str(uuid.uuid4())}">')
    for obj_id, it_uuid in build_items:
        xml_lines.append(f'    <item objectid="{obj_id}" p:UUID="{it_uuid}"/>')
    xml_lines.append('  </build>')
    xml_lines.append('</model>')

    model_str = '\n'.join(xml_lines)

    content_types = '''<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
</Types>'''

    rels = '''<?xml version="1.0" encoding="utf-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel" Target="/3D/3dmodel.model" Id="rel0"/>
</Relationships>'''

    # Bestemming in models/
    models_dir = os.path.join(REPO_ROOT, "models")
    os.makedirs(models_dir, exist_ok=True)
    out_3mf = os.path.join(models_dir, "Kenteken_Sleutelhanger.3mf")

    with zipfile.ZipFile(out_3mf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model_str)

    # Ook root link/kopie updaten
    root_3mf = os.path.join(REPO_ROOT, "Kenteken_Sleutelhanger.3mf")
    shutil.copyfile(out_3mf, root_3mf)

    print(f"\nKlaar! Universeel multi-color 3MF bestand succesvol gegenereerd:")
    print(f"-> {out_3mf}")

if __name__ == "__main__":
    main()
