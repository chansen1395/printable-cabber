# CAD: parametric model and STLs

One script, [cabber.py](cabber.py) (CadQuery 2.8), builds every part. Only one configuration has passed the checks: a 4,000 RPM motor, a 14 in bolt and 1½ in wheels. The parameters at the top of the script can be changed, but other values are untested and some fail the check (a 12 in bolt, 6,000 and 8,000 RPM motors). The script reports whether the bolt is long enough and how many teeth the printed pulley needs.

```text
python cad/cabber.py                 # STLs, STEPs, renders (the renders need pyvista; add --no-render to skip them)
python cad/check_clashes.py          # interference, clearance, STL, bed and bolt-stack checks
python tools/print_table.py          # refresh the print table below
```

- [stl/](stl/): one STL per printed part, already oriented for printing.
- [step/](step/): each part, plus [cabber_assembly.step](step/cabber_assembly.step).
- [../renders/](../renders/): the assembly views, drawn with a z-buffer (VTK), plus `portfolio_assembly.png` (1800 × 1200, white background).

Checked on 2026-11-03: all 17 parts are valid, single-solid and watertight, they fit the 420 × 420 mm bed, no two bodies overlap (exact boolean, cross-checked on meshes), the wheels and the end disk keep at least 5 mm from the hood, pan and shroud, the sliding tank keeps 3 mm, and the bolt stack fits the 14 in bolt. `check_clashes.py` prints the minimum gap of every moving part and tests itself on a dropped hood and a wheel pushed at the pan before it judges the model.

## Printing (PETG, 240 °C, bed 75–80 °C, no supports)

<!-- PRINT TABLE -->
| STL | Qty | On the bed X × Y × H (mm) | Fits 420 × 420 | Layer (mm) | Walls | Top/bottom | Infill | Mass (g) | Time (h) | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
| `pedestal_L.stl` | 1 | 44 × 110 × 209 | yes | 0.24 | 4 | 5/5 | 25 % gyroid | ~208 | ~6 | Base on bed. M4 nuts slide into the side slots. |
| `pedestal_R.stl` | 1 | 44 × 110 × 209 | yes | 0.24 | 4 | 5/5 | 25 % gyroid | ~208 | ~6 | Same as pedestal_L. |
| `bearing_cap.stl` | 2 | 18 × 64 × 24 | yes | 0.2 | 4 | 5/5 | 40 % | ~27 | ~1 | Print 2. |
| `arbor_pulley.stl` | 1 | 40 × 40 × 28 | yes | 0.12 | 6 | 6/6 | 100 % | ~24 | ~1 | Hex hub on bed; fine layers for the GT2 teeth. |
| `bushing.stl` | 4 | 25 × 25 × 37 | yes | 0.2 | 4 | - | 100 % | ~68 | ~2 | Print 4. |
| `spacer_A.stl` | 1 | 40 × 40 × 14 | yes | 0.2 | 6 | 6/6 | 100 % | ~7 | ~0 | Solid: carries the clamp on the bearing race. |
| `spacer_gap.stl` | 3 | 40 × 40 × 31 | yes | 0.2 | 4 | 5/5 | 50 % | ~48 | ~1 | Print 3. |
| `spacer_B.stl` | 1 | 40 × 40 × 14 | yes | 0.2 | 6 | 6/6 | 100 % | ~7 | ~0 | Solid. |
| `spacer_C.stl` | 1 | 40 × 40 × 14 | yes | 0.2 | 6 | 6/6 | 100 % | ~7 | ~0 | Solid. |
| `pan.stl` | 1 | 262 × 215 × 191 | yes | 0.28 | 3 | 4/4 | 15 % | ~464 | ~13 | Upright. |
| `hood.stl` | 1 | 159 × 194 × 255 | yes | 0.28 | 3 | - | - | ~321 | ~9 | Stand on one end; 8 mm brim. |
| `disk_shroud.stl` | 1 | 310 × 192 × 42 | yes | 0.28 | 3 | 4/4 | 15 % | ~195 | ~5 | Inner wall on bed. |
| `backing_plate.stl` | 1 | 152 × 152 × 13 | yes | 0.2 | 4 | 5/5 | 30 % | ~124 | ~3 | Disk face on bed. |
| `tank.stl` | 1 | 230 × 292 × 108 | yes | 0.28 | 4 | 5/5 | 15 % | ~591 | ~17 | 4 walls so it holds water. |
| `motor_cradle.stl` | 1 | 74 × 62 × 27 | yes | 0.24 | 4 | 5/5 | 25 % | ~40 | ~1 |  |
| `motor_strap.stl` | 1 | 50 × 54 × 24 | yes | 0.24 | 4 | 5/5 | 40 % | ~15 | ~0 |  |
| `control_mount.stl` | 1 | 70 × 45 × 80 | yes | 0.28 | 3 | 3/3 | 15 % | ~52 | ~1 |  |
| **Total** | | | | | | | | **~2.4 kg** | **~68 h** | |
<!-- /PRINT TABLE -->

## Fits

| Where | Modeled | Fits |
|---|---|---|
| Bores on the bolt | Ø13.0 | 1/2 in bolt, slide fit |
| Bushing OD | Ø25.2, 1.5 mm shorter than the wheel | 1 in wheel bore |
| Pulley hex pocket | 19.45 A/F, 8.6 deep | 1/2 in bolt head (3/4 in A/F) |
| Arbor pulley | GT2, 53 teeth for a 4,000 RPM motor | GT2 6 mm belt |
| Bearing pockets | Ø28.8 × bearing width, with lips | R8-2RS. Tape one wrap round the bearing if it's loose. |
| Bearing caps, motor strap | M4 × 30 into nut slots | |
| Motor cradle | saddle for `motor_d` (42 mm for a 775), slotted base | |
| Drip ports | Ø6.3 | 6 mm airline tube, push-fit |
| Board screws | Ø4.5 | #8 wood screws |
