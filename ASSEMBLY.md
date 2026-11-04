# Assembly

Parts: [BOM.md](BOM.md). Prints: [cad/README.md](cad/README.md).

**Tools:** screwdriver, 3/4 in wrench, hex keys, soldering iron or crimp connectors for 4 wires.

## 1. Print

Print the 17 parts from `cad/stl/` (estimated ~68 h). The model passes its checks only for the motor, bolt and wheels in [BOM.md](BOM.md) (4,000 RPM motor, 14 in bolt, 1½ in wheels), so buy those. Test early: a bushing in a wheel, a spacer on the bolt, the bolt head in the pulley's hex.

## 2. Base

1. Screw **pedestal_L** to the board, 170 mm from the left end and centered front to back (4 wood screws).
2. Slide M4 nuts into the side slots of both pedestals.
3. Stand **pedestal_R** 281 mm to the right (center to center). Screw it down later.

## 3. Arbor

1. On the bolt, from the head end: **arbor pulley** (head in the hex) → **bearing** → **spacer_A** → **W1** (80) with a **bushing** → **spacer_gap** → **W2** → **spacer_gap** → **W3** → **spacer_gap** → **W4** (600) → **spacer_B** → **bearing** → **spacer_C**.
2. Set the **tank** between the pedestals and the **pan** on the pedestal ledges.
3. Lower the arbor in so the bearings drop into the pedestal pockets. Line up pedestal_R and screw it down. Fit the **bearing caps** (2 × M4 × 30 each).
4. Lower the **disk_shroud** over the bolt end and screw its feet to the board. Then fit the **backing plate**, fender washer and nut. Snug the nut (about 5 N·m) and tighten the caps.
5. Set the **hood** on: it hooks over the pan's back wall and rests on the two ledges.

## 4. Motor

1. Push the **GT2 20T pulley** onto the motor shaft and tighten its set screw.
2. Clamp the motor in the **motor_cradle** with the **motor_strap** (4 × M4 × 30).
3. Loop the GT2 belt on, slide the cradle back until the belt is snug, and screw it down through the slots. Line the two pulleys up with a straightedge.

## 5. Wiring and water

Wire it per [WIRING.md](WIRING.md) and zip-tie the PWM board to the **control_mount**. Put the pump behind the weir. Run airline tube from the pump through the valves (zip-tied to the pan's back wall) into the four hood ports. Put a cup under the shroud spout and keep a squeeze bottle for the end disk.

## 6. First run

Knob at zero, switch on, then speed up slowly. Check the wheel tops move toward you. Run 5 minutes dry, then 5 minutes with water. Try a first stone on W1 with light pressure.

## Upkeep

- Re-snug the arbor nut after the first hour.
- Change the water when it turns milky.
- Dress glazed wheels.
- **Wheel change:** nut and disk off, shroud off, caps off; lift the arbor out and swap the wheels on the bench.
