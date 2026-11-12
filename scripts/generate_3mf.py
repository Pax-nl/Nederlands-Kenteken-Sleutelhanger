#!/usr/bin/env python3
"""
Genereert een native Bambu Studio multi-part / multi-color .3mf project
voor de Nederlandse Kenteken Sleutelhanger conform de MSX Cartridge pipeline.
"""

import os
import sys
import json
import time
import uuid
import struct
import shutil
import zipfile
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
TEMPLATE_PATH = REPO_ROOT / "templates" / "bambu_template.3mf"
SCAD_FILE = REPO_ROOT / "Kenteken_Sleutelhanger.scad"
OUTPUT_3MF = REPO_ROOT / "models" / "Kenteken_Sleutelhanger.3mf"

PARTS_CONFIG = [
    {
        "arg": "black",
        "name": "Basis_Zwart",
        "color": "#111111FF",
        "paint_color": "#111111",
        "extruder": 1,
    },
    {
        "arg": "yellow",
        "name": "Plaat_Geel",
        "color": "#FFCC00FF",
        "paint_color": "#FFCC00",
        "extruder": 2,
    },
    {
        "arg": "blue",
        "name": "Vlak_Blauw",
        "color": "#003399FF",
        "paint_color": "#003399",
        "extruder": 3,
    },
    {
        "arg": "white",
        "name": "Opdruk_Wit",
        "color": "#FFFFFFFF",
        "paint_color": "#FFFFFF",
        "extruder": 4,
    },
]

def find_openscad() -> str:
    paths = [
        "openscad",
        "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD",
        os.path.expanduser("~/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"),
    ]
    for p in paths:
        if shutil.which(p) or os.path.isfile(p):
            return p
    return "openscad"

def parse_stl(path: Path) -> list[tuple[tuple[float, float, float], ...]]:
    """Parseer een binary of ASCII STL bestand naar een lijst van driehoeken."""
    with open(path, "rb") as f:
        header = f.read(80)
        count_bytes = f.read(4)
        if len(count_bytes) == 4:
            count = struct.unpack("<I", count_bytes)[0]
            sz = os.path.getsize(path)
            if sz == 84 + count * 50:
                triangles = []
                for _ in range(count):
                    data = f.read(50)
                    if len(data) < 50:
                        break
                    v1 = struct.unpack("<3f", data[12:24])
                    v2 = struct.unpack("<3f", data[24:36])
                    v3 = struct.unpack("<3f", data[36:48])
                    triangles.append((v1, v2, v3))
                return triangles

        # Fallback naar ASCII
        f.seek(0)
        import re
        text = f.read().decode("utf-8", errors="ignore")
        pts = [
            tuple(map(float, m.groups()))
            for m in re.finditer(r"vertex\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)", text)
        ]
        triangles = []
        for i in range(0, len(pts) - 2, 3):
            triangles.append((pts[i], pts[i + 1], pts[i + 2]))
        return triangles

def triangles_to_mesh(
    triangles: list[tuple[tuple[float, float, float], ...]],
) -> tuple[list[tuple[float, float, float]], list[list[int]]]:
    """Dedupliceer vertices en maak geïndexeerde triangle faces met behoud van vertex-volgorde."""
    vertices: list[tuple[float, float, float]] = []
    v_map: dict[tuple[float, float, float], int] = {}
    indices: list[list[int]] = []
    for tri in triangles:
        tri_idx: list[int] = []
        for v in tri:
            key = (round(v[0], 4), round(v[1], 4), round(v[2], 4))
            idx = v_map.get(key)
            if idx is None:
                idx = len(vertices)
                v_map[key] = idx
                vertices.append(key)
            tri_idx.append(idx)
        indices.append(tri_idx)
    return vertices, indices

def main():
    openscad = find_openscad()
    if not SCAD_FILE.is_file():
        print(f"Fout: Kan {SCAD_FILE} niet vinden!")
        sys.exit(1)
    if not TEMPLATE_PATH.is_file():
        print(f"Fout: Kan template {TEMPLATE_PATH} niet vinden!")
        sys.exit(1)

    print(f"1. OpenSCAD: {openscad}")
    print("2. Exporteren van individuele kleuronderdelen via OpenSCAD...")

    parts_data = []
    try:
        for idx, cfg in enumerate(PARTS_CONFIG, start=1):
            stl_path = SCRIPT_DIR / f"_temp_{cfg['arg']}.stl"
            cmd = [
                openscad,
                "-D", f'part="{cfg["arg"]}"',
                "-o", str(stl_path),
                str(SCAD_FILE),
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            tris = parse_stl(stl_path)
            verts, indices = triangles_to_mesh(tris)

            xs = [v[0] for v in verts]
            ys = [v[1] for v in verts]
            zs = [v[2] for v in verts]
            cx = (min(xs) + max(xs)) / 2.0
            cy = (min(ys) + max(ys)) / 2.0
            cz = (min(zs) + max(zs)) / 2.0

            parts_data.append({
                "id": idx,
                "name": cfg["name"],
                "verts": verts,
                "indices": indices,
                "cx": cx,
                "cy": cy,
                "cz": cz,
                "color": cfg["color"],
                "paint_color": cfg["paint_color"],
                "extruder": cfg["extruder"],
                "uuid": str(uuid.uuid4()),
            })
            print(f"   - {cfg['name']}: {len(verts)} vertices, {len(indices)} driehoeken (Extruder {cfg['extruder']})")
    finally:
        for cfg in PARTS_CONFIG:
            p = SCRIPT_DIR / f"_temp_{cfg['arg']}.stl"
            if p.exists():
                p.unlink()

    print("3. Genereren van Bambu Studio projectstructuur conform MSX pipeline...")
    ref = parts_data[0]
    ref_cx, ref_cy, ref_cz = ref["cx"], ref["cy"], ref["cz"]

    # 1. Build 3D/Objects/object_1.model (Local coordinates centered on each part)
    colorgroup_id = 100
    obj_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
        'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
        'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" '
        'xmlns:m="http://schemas.microsoft.com/3dmanufacturing/material/2015/02" '
        'requiredextensions="p">',
        ' <metadata name="BambuStudio:3mfVersion">1</metadata>',
        ' <resources>',
        f'  <m:colorgroup id="{colorgroup_id}">',
    ]
    for p in parts_data:
        obj_lines.append(f'   <m:color color="{p["color"]}"/>')
    obj_lines.append('  </m:colorgroup>')

    for color_idx, p in enumerate(parts_data):
        obj_uuid = f"0001{p['id']:04x}-81cb-4c03-9d28-80fed5dfa1dc"
        paint_attr = p["paint_color"]
        obj_lines.append(
            f'  <object id="{p["id"]}" pid="{colorgroup_id}" pindex="{color_idx}" '
            f'p:UUID="{obj_uuid}" type="model">'
        )
        obj_lines.append('   <mesh>')
        obj_lines.append('    <vertices>')
        pcx, pcy, pcz = p["cx"], p["cy"], p["cz"]
        for v in p["verts"]:
            obj_lines.append(
                f'     <vertex x="{(v[0] - pcx):.6f}" y="{(v[1] - pcy):.6f}" z="{(v[2] - pcz):.6f}"/>'
            )
        obj_lines.append('    </vertices>')
        obj_lines.append('    <triangles>')
        for t in p["indices"]:
            obj_lines.append(
                f'     <triangle v1="{t[0]}" v2="{t[1]}" v3="{t[2]}" '
                f'pid="{colorgroup_id}" p1="{color_idx}" paint_color="{paint_attr}"/>'
            )
        obj_lines.append('    </triangles>')
        obj_lines.append('   </mesh>')
        obj_lines.append('  </object>')

    obj_lines.append(' </resources>')
    obj_lines.append(' <build/>')
    obj_lines.append('</model>')
    object_1_model = '\n'.join(obj_lines)

    # 2. Build 3D/3dmodel.model
    container_id = 5
    now_date = time.strftime("%Y-%m-%d")
    project_title = "Kenteken Sleutelhanger"

    model_3d_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
        'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
        'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" '
        'xmlns:m="http://schemas.microsoft.com/3dmanufacturing/material/2015/02" '
        'requiredextensions="p">',
        ' <metadata name="Application">BambuStudio-02.09.01.70</metadata>',
        ' <metadata name="BambuStudio:3mfVersion">1</metadata>',
        ' <metadata name="Copyright"></metadata>',
        f' <metadata name="CreationDate">{now_date}</metadata>',
        ' <metadata name="Description"></metadata>',
        ' <metadata name="Designer"></metadata>',
        ' <metadata name="DesignerCover"></metadata>',
        ' <metadata name="DesignerUserId"></metadata>',
        ' <metadata name="License"></metadata>',
        f' <metadata name="ModificationDate">{now_date}</metadata>',
        ' <metadata name="Origin"></metadata>',
        ' <metadata name="ProfileCover"></metadata>',
        ' <metadata name="ProfileDescription"></metadata>',
        ' <metadata name="ProfileTitle"></metadata>',
        ' <metadata name="Thumbnail_Middle">/Metadata/plate_1.png</metadata>',
        ' <metadata name="Thumbnail_Small">/Metadata/plate_1_small.png</metadata>',
        f' <metadata name="Title">{project_title}</metadata>',
        ' <resources>',
        f'  <object id="{container_id}" p:UUID="00000001-61cb-4c03-9d28-80fed5dfa1dc" type="model">',
        '   <components>',
    ]

    for p in parts_data:
        comp_uuid = f"0001{p['id'] - 1:04x}-b206-40ff-9872-83e8017abed1"
        dx = p["cx"] - ref_cx
        dy = p["cy"] - ref_cy
        dz = p["cz"] - ref_cz
        transform_str = f"1 0 0 0 1 0 0 0 1 {dx:.8f} {dy:.8f} {dz:.8f}"
        model_3d_lines.append(
            f'    <component p:path="/3D/Objects/object_1.model" objectid="{p["id"]}" '
            f'p:UUID="{comp_uuid}" transform="{transform_str}"/>'
        )
    model_3d_lines.append('   </components>')
    model_3d_lines.append('  </object>')
    model_3d_lines.append(' </resources>')
    model_3d_lines.append(' <build p:UUID="2c7c17d8-22b5-4d84-8835-1976022ea369">')
    model_3d_lines.append(
        f'  <item objectid="{container_id}" p:UUID="00000005-b1ec-4553-aec9-835e5b724bb4" '
        f'transform="1 0 0 0 1 0 0 0 1 128 128 {ref_cz:.8f}" printable="1"/>'
    )
    model_3d_lines.append(' </build>')
    model_3d_lines.append('</model>')
    model_3d = '\n'.join(model_3d_lines)

    # 3. Build Metadata/model_settings.config
    settings_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<config>',
        f'  <object id="{container_id}">',
        f'    <metadata key="name" value="{project_title}"/>',
        '    <metadata key="extruder" value="1"/>',
        f'    <metadata face_count="{sum(len(p["indices"]) for p in parts_data)}"/>',
    ]

    for p in parts_data:
        dx = p["cx"] - ref_cx
        dy = p["cy"] - ref_cy
        dz = p["cz"] - ref_cz
        matrix_str = f"1 0 0 {dx:.16f} 0 1 0 {dy:.16f} 0 0 1 {dz:.16f} 0 0 0 1" if (dx or dy or dz) else "1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"
        settings_lines.append(f'    <part id="{p["id"]}" subtype="normal_part" uuid="{p["uuid"]}">' )
        settings_lines.append(f'      <metadata key="name" value="{p["name"]}"/>')
        settings_lines.append(f'      <metadata key="matrix" value="{matrix_str}"/>')
        settings_lines.append(f'      <metadata key="source_file" value="{p["name"]}.stl"/>')
        settings_lines.append('      <metadata key="source_object_id" value="0"/>')
        settings_lines.append('      <metadata key="source_volume_id" value="0"/>')
        settings_lines.append('      <metadata key="source_offset_x" value="0"/>')
        settings_lines.append('      <metadata key="source_offset_y" value="0"/>')
        settings_lines.append(f'      <metadata key="source_offset_z" value="{ref_cz:.1f}"/>')
        settings_lines.append(f'      <metadata key="extruder" value="{p["extruder"]}"/>')
        settings_lines.append(
            f'      <mesh_stat face_count="{len(p["indices"])}" edges_fixed="0" '
            'degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>'
        )
        settings_lines.append('    </part>')

    settings_lines.append('  </object>')
    settings_lines.append('  <plate>')
    settings_lines.append('    <metadata key="plater_id" value="1"/>')
    settings_lines.append('    <metadata key="plater_name" value=""/>')
    settings_lines.append('    <metadata key="locked" value="false"/>')
    settings_lines.append('    <metadata key="filament_map_mode" value="Auto For Flush"/>')
    settings_lines.append('    <metadata key="filament_maps" value="1 2 3 4"/>')
    settings_lines.append('    <metadata key="filament_volume_maps" value="0 0 0 0"/>')
    settings_lines.append('    <model_instance>')
    settings_lines.append(f'      <metadata key="object_id" value="{container_id}"/>')
    settings_lines.append('      <metadata key="instance_id" value="0"/>')
    settings_lines.append('      <metadata key="identify_id" value="114"/>')
    settings_lines.append('    </model_instance>')
    settings_lines.append('  </plate>')
    settings_lines.append('  <assemble>')
    settings_lines.append(
        f'   <assemble_item object_id="{container_id}" instance_id="0" '
        f'transform="1 0 0 0 1 0 0 0 1 0 0 {ref_cz:.1f}" offset="0 0 0" />'
    )
    for idx in range(len(parts_data)):
        settings_lines.append(
            f'   <assemble_item object_id="{container_id}" volume_id="{idx}" '
            'transform="1 0 0 0 1 0 0 0 1 0 0 0" />'
        )
    settings_lines.append('  </assemble>')
    settings_lines.append('</config>')
    model_settings = '\n'.join(settings_lines)

    # 4. Pack into template
    OUTPUT_3MF.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(TEMPLATE_PATH, "r") as src:
        with zipfile.ZipFile(OUTPUT_3MF, "w", compression=zipfile.ZIP_DEFLATED) as dst:
            for item in src.infolist():
                if item.filename in (
                    "3D/3dmodel.model",
                    "3D/Objects/object_1.model",
                    "Metadata/model_settings.config",
                ):
                    continue
                data = src.read(item.filename)

                if item.filename == "Metadata/project_settings.config":
                    try:
                        cfg = json.loads(data.decode("utf-8"))
                        cfg["filament_colour"] = ["#111111", "#FFCC00", "#003399", "#FFFFFF"]
                        cfg["filament_multi_colour"] = ["#111111", "#FFCC00", "#003399", "#FFFFFF"]
                        cfg["filament_type"] = ["PLA", "PLA", "PLA", "PLA"]
                        cfg["filament_map"] = ["1", "2", "3", "4"]
                        cfg["default_filament_colour"] = ["#111111", "#FFCC00", "#003399", "#FFFFFF"]
                        cfg["wipe_tower_x"] = ["210.0"]
                        cfg["wipe_tower_y"] = ["210.0"]
                        data = json.dumps(cfg, indent=4).encode("utf-8")
                    except Exception:
                        pass
                elif item.filename == "Metadata/plate_1.json":
                    try:
                        pl = json.loads(data.decode("utf-8"))
                        for obj in pl.get("bbox_objects", []):
                            if obj.get("name") == "wipe_tower":
                                obj["bbox"] = [210.0, 210.0, 245.0, 244.0]
                        data = json.dumps(pl, indent=2).encode("utf-8")
                    except Exception:
                        pass

                dst.writestr(item, data)

            dst.writestr("3D/3dmodel.model", model_3d.encode("utf-8"))
            dst.writestr("3D/Objects/object_1.model", object_1_model.encode("utf-8"))
            dst.writestr("Metadata/model_settings.config", model_settings.encode("utf-8"))

    print(f"\nKlaar! Native Bambu Studio 3MF succesvol gegenereerd conform MSX Cartridge pipeline:\n-> {OUTPUT_3MF}")

if __name__ == "__main__":
    main()
