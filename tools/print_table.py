"""Write the print table section of cad/README.md from cad/print_table.json.

Mass = solid volume x 1.27 g/cm3 (PETG) x fill factor; time = volume / effective rate.
Both are planning estimates; the slicer gives the real numbers.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RATE_CM3_H = 28.0      # effective PETG throughput at 0.24-0.28 mm on a 420 x 420 mm bed, including travel (estimate)
DENSITY = 1.27

SETTINGS = {
    # part: (layer, walls, top/bottom, infill, fill_factor, notes)
    "pedestal_L": ("0.24", 4, "5/5", "25 % gyroid", 0.55, "Base on bed. M4 nuts slide into the side slots."),
    "pedestal_R": ("0.24", 4, "5/5", "25 % gyroid", 0.55, "Same as pedestal_L."),
    "bearing_cap": ("0.2", 4, "5/5", "40 %", 0.8, "Print 2."),
    "arbor_pulley": ("0.12", 6, "6/6", "100 %", 1.0, "Hex hub on bed; fine layers for the GT2 teeth."),
    "bushing": ("0.2", 4, "-", "100 %", 1.0, "Print 4."),
    "spacer_A": ("0.2", 6, "6/6", "100 %", 1.0, "Solid: carries the clamp on the bearing race."),
    "spacer_gap": ("0.2", 4, "5/5", "50 %", 0.85, "Print 3."),
    "spacer_B": ("0.2", 6, "6/6", "100 %", 1.0, "Solid."),
    "spacer_C": ("0.2", 6, "6/6", "100 %", 1.0, "Solid."),
    "pan": ("0.28", 3, "4/4", "15 %", 0.9, "Upright."),
    "hood": ("0.28", 3, "-", "-", 0.95, "Stand on one end; 8 mm brim."),
    "disk_shroud": ("0.28", 3, "4/4", "15 %", 0.9, "Inner wall on bed."),
    "backing_plate": ("0.2", 4, "5/5", "30 %", 0.75, "Disk face on bed."),
    "tank": ("0.28", 4, "5/5", "15 %", 0.95, "4 walls so it holds water."),
    "motor_cradle": ("0.24", 4, "5/5", "25 %", 0.7, ""),
    "motor_strap": ("0.24", 4, "5/5", "40 %", 0.8, ""),
    "control_mount": ("0.28", 3, "3/3", "15 %", 0.9, ""),
}


def main():
    data = json.load(open(os.path.join(ROOT, "cad", "print_table.json")))
    rows, tot_g, tot_h = [], 0.0, 0.0
    for p in data["parts"]:
        name = p["part"]
        layer, walls, tb, infill, ff, note = SETTINGS[name]
        g = p["solid_cm3"] * DENSITY * ff * p["qty"]
        h = p["solid_cm3"] * ff * p["qty"] / RATE_CM3_H
        tot_g += g
        tot_h += h
        rows.append(f"| `{name}.stl` | {p['qty']} | {p['bed_x']:.0f} × {p['bed_y']:.0f} × {p['height']:.0f} | "
                    f"{'yes' if p['fits_420_bed'] else '**NO**'} | {layer} | {walls} | {tb} | {infill} | ~{g:.0f} | ~{h:.0f} | {note} |")
    out = ["| STL | Qty | On the bed X × Y × H (mm) | Fits 420 × 420 | Layer (mm) | Walls | Top/bottom | Infill | Mass (g) | Time (h) | Notes |",
           "|---|---|---|---|---|---|---|---|---|---|---|"] + rows
    out.append(f"| **Total** | | | | | | | | **~{tot_g / 1000:.1f} kg** | **~{tot_h:.0f} h** | |")
    text = "\n".join(out)
    path = os.path.join(ROOT, "cad", "README.md")
    src = open(path, encoding="utf-8").read()
    start, end = src.index("<!-- PRINT TABLE -->"), src.index("<!-- /PRINT TABLE -->")
    src = src[:start] + "<!-- PRINT TABLE -->\n" + text + "\n" + src[end:]
    open(path, "w", encoding="utf-8", newline="\n").write(src)
    print(text)


if __name__ == "__main__":
    main()
