"""Parametric model of the low-cost 6-inch cabber: 4 wheels + end disk on a 1/2-13 hex bolt.

Run from the repo root, in a venv with requirements.txt installed:
    python cad/cabber.py            # STLs, STEPs, renders and cad/print_table.json
    python cad/cabber.py --no-render

Coordinates (mm): X along the arbor (left -> right), Y front (-) to back (+), Z up from the bench.
Every printed part is built in its assembled position; PRINTED says which face goes on the bed.
Bought parts are simple stand-ins sized from their listings.

Only the defaults below have passed cad/check_clashes.py (4,000 RPM motor, 14 in bolt, 1.5 in wheels). Other values of
these are untested and some fail: motor_rpm (12 V no-load speed of the 775 motor), motor_d, wheel_w, bolt_len_in,
bolt_thread_in. The script checks the bolt and picks the arbor pulley's tooth count.
"""
import json
import math
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_STL = os.path.join(HERE, "stl")
OUT_STEP = os.path.join(HERE, "step")
OUT_RENDER = os.path.join(os.path.dirname(HERE), "renders")
IN = 25.4

# ----------------------------------------------------------------------------------------------
# Parameters
# ----------------------------------------------------------------------------------------------
P = dict(
    Zs=228.0,                       # arbor center height above the bench
    # base: 1x12 pine shelf board (actual 3/4 x 11-1/4 in), 24 in long
    board_l=610.0, board_w=286.0, board_t=19.0, board_x0=-170.0,
    # arbor: 1/2-13 hex bolt (hex cap screw); the head stays on and drives the pulley
    bolt_d=12.7, bolt_len_in=14.0, bolt_thread_in=1.5, head_af=19.05, head_h=7.9,
    nut_h=11.1, washer_od=38.1, washer_t=2.4,      # 1/2 x 1-1/2 in fender washer
    # bearings: R8-2RS (1/2 x 1-1/8 x 5/16 in)
    brg_od=28.575, brg_w=7.94, brg_race_d=16.0,    # race_d: the most a spacer may touch (inner race)
    housing_od=48.0, tower_w=18.0, ped_base_x=44.0, ped_base_y=110.0, ped_base_t=6.0, lip_r=12.8,
    # wheels 6 x 1-1/2 in with 1 in bore, on printed 1 in -> 1/2 in bushings
    wheel_d=152.4, wheel_w=38.1, wheel_bore=25.4, n_wheels=4, gap=31.0, face_d=40.0, clr_bore=0.3, wall_gap=5.5,
    # water: printed tank with a built-in weir; 12 V mini pump behind the weir
    tank_x=230.0, tank_y=280.0, tank_h=108.0, tank_wall=2.4, tank_floor=3.0, weir_y=95.0, weir_h=70.0,
    pan_front=-112.0, pan_back=100.0, pan_t=3.0, pan_gap=3.0, wall_t=3.0, slot_w=26.0,
    hood_r=90.0, hood_t=3.0, hood_front_deg=15.0,
    # drive: 775 DC motor (12 V) -> GT2 6 mm belt -> printed GT2 arbor pulley
    motor_rpm=4000.0, arbor_rpm=1500.0, z_motor=20, gt2_belt=500.0,
    motor_d=42.0, motor_len=67.0, motor_shaft_len=17.0, motor_slot=12.0,
    # end disk (printed backing plate for hook-and-loop pads)
    disk_d=152.4, disk_t=6.0, disk_hub_l=7.0, shroud_r=90.0, shroud_t=3.0,
)


def gt2_pd(z):
    return z * 2.0 / math.pi


def layout():
    """X positions along the arbor (bearing L center at X = 0) and the drive geometry."""
    L = {}
    bw2 = P["brg_w"] / 2
    th = P["tower_w"] / 2
    L["x_brg_L"] = 0.0
    # arbor pulley, inboard to outboard: race hub (touches the inner race only), flange, GT2 teeth, flange, hex hub
    L["x_race_hub"] = (-bw2 - 7.0, -bw2)
    x = L["x_race_hub"][0]
    L["x_teeth"] = (x - 1.5 - 8.0, x - 1.5)
    L["xb"] = sum(L["x_teeth"]) / 2                              # belt plane
    L["x_hex_hub"] = (L["x_teeth"][0] - 1.5 - 10.0, L["x_teeth"][0] - 1.5)
    L["x_head_under"] = L["x_hex_hub"][0] + 8.6                  # pocket floor = head underside
    L["x_wall_L"] = (th + 0.5, th + 0.5 + P["wall_t"])
    x = L["x_wall_L"][1] + P["wall_gap"]                         # W1 left face
    L["x_spA"] = (bw2, x)
    L["x_wheels"], L["x_gaps"] = [], []
    for i in range(P["n_wheels"]):
        L["x_wheels"].append((x, x + P["wheel_w"])); x += P["wheel_w"]
        if i < P["n_wheels"] - 1:
            L["x_gaps"].append((x, x + P["gap"])); x += P["gap"]
    L["x_wall_R"] = (x + P["wall_gap"], x + P["wall_gap"] + P["wall_t"])
    L["x_brg_R"] = L["x_wall_R"][1] + 0.5 + th
    L["x_spB"] = (x, L["x_brg_R"] - bw2)
    xr = L["x_brg_R"] + th + 1.0                                 # shroud wall just outboard of pedestal_R
    L["x_shroud_wall"] = (xr, xr + P["shroud_t"])
    L["x_spC"] = (L["x_brg_R"] + bw2, L["x_shroud_wall"][1] + 5.5)
    L["x_disk_hub"] = (L["x_spC"][1], L["x_spC"][1] + P["disk_hub_l"])
    L["x_disk"] = (L["x_disk_hub"][1], L["x_disk_hub"][1] + P["disk_t"])
    L["x_disk_face"] = L["x_disk"][1]
    L["x_washer"] = (L["x_disk_face"], L["x_disk_face"] + P["washer_t"])
    L["x_nut"] = (L["x_washer"][1], L["x_washer"][1] + P["nut_h"])
    L["x_bolt_tip"] = L["x_head_under"] + P["bolt_len_in"] * IN
    L["x_thread_start"] = L["x_bolt_tip"] - P["bolt_thread_in"] * IN
    L["stack_ok"] = L["x_thread_start"] <= L["x_washer"][1] and L["x_nut"][1] + 1.0 <= L["x_bolt_tip"]
    L["z_tank_rim"] = P["board_t"] + P["tank_h"]
    L["z_pan"] = L["z_tank_rim"] + P["pan_gap"]
    c = (th + L["x_brg_R"] - th) / 2
    L["x_tank"] = (c - P["tank_x"] / 2, c + P["tank_x"] / 2)
    # drive: arbor teeth from the speed ratio; motor slides back until the GT2 loop is snug
    L["z_arbor"] = max(36, round(P["z_motor"] * P["motor_rpm"] / P["arbor_rpm"]))
    d1, d2 = gt2_pd(P["z_motor"]), gt2_pd(L["z_arbor"])
    b = P["gt2_belt"] - math.pi * (d1 + d2) / 2
    C = (b + math.sqrt(b * b - 2 * (d2 - d1) ** 2)) / 4
    L["z_motor_axis"] = P["board_t"] + 6.0 + P["motor_d"] / 2
    L["belt_C"] = C
    L["motor_y"] = math.sqrt(max(C ** 2 - (P["Zs"] - L["z_motor_axis"]) ** 2, 0.0))
    L["arbor_max_rpm"] = P["motor_rpm"] * P["z_motor"] / L["z_arbor"]
    L["x_motor_face"] = L["xb"] - 4.0 - 1.0 - 7.0 - 1.0           # half teeth, flange, aluminum pulley hub, gap
    return L


L = layout()
Zs = P["Zs"]


# ----------------------------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------------------------
def box(x0, x1, y0, y1, z0, z1):
    return cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).translate((x0, y0, z0))


def cyl_x(x0, x1, r, y=0.0, z=None):
    z = Zs if z is None else z
    return cq.Workplane("YZ").circle(r).extrude(x1 - x0).translate((x0, y, z))


def cyl_z(z0, z1, r, x, y):
    return cq.Workplane("XY").circle(r).extrude(z1 - z0).translate((x, y, z0))


def prism_yz(pts, x0, x1):
    return cq.Workplane("YZ").polyline(pts).close().extrude(x1 - x0).translate((x0, 0, 0))


def prism_xz(pts, y0, y1):
    return cq.Workplane("XZ").polyline(pts).close().extrude(-(y1 - y0)).translate((0, y0, 0))


def arc_pts(r, t0, t1, n=72, yc=0.0, zc=None):
    """Circle points in the YZ plane; t measured from the front (-Y) upward over the top."""
    zc = Zs if zc is None else zc
    return [(yc - r * math.cos(math.radians(t0 + (t1 - t0) * i / n)), zc + r * math.sin(math.radians(t0 + (t1 - t0) * i / n)))
            for i in range(n + 1)]


def hex_x(x0, x1, af, y=0.0, z=None):
    z = Zs if z is None else z
    return cq.Workplane("YZ").polygon(6, af / math.cos(math.radians(30))).extrude(x1 - x0).translate((x0, y, z))


def screw_hole_z(x, y, z0, z1, d=4.5):
    """Clearance hole for a #8 wood screw (or M4)."""
    return cyl_z(z0, z1, d / 2, x, y)


def gt2_teeth(z, x0, x1, y=0.0, zc=None):
    """Printed GT2 pulley teeth: OD = PD - 0.508; each gap a 1.1 mm slot with a round bottom, 0.75 deep."""
    zc = Zs if zc is None else zc
    od = gt2_pd(z) - 0.508
    sk = cq.Workplane("YZ").circle(od / 2)
    body = sk.extrude(x1 - x0).translate((x0, y, zc))
    gap = cq.Workplane("YZ").center(0, od / 2 - 0.2).rect(1.1, 0.8).extrude(x1 - x0 + 2).union(
        cq.Workplane("YZ").center(0, od / 2 - 0.75 + 0.55).circle(0.55).extrude(x1 - x0 + 2))
    for i in range(z):
        g = gap.rotate((0, 0, 0), (1, 0, 0), i * 360.0 / z).translate((x0 - 1, y, zc))
        body = body.cut(g)
    return body


# ----------------------------------------------------------------------------------------------
# Printed parts
# ----------------------------------------------------------------------------------------------
def pedestal(xc, side):
    """Bearing pedestal: wood-screwed to the board; open-top pocket the width of the bearing, with lips; pan ledge."""
    zb = P["board_t"]
    th = P["tower_w"] / 2
    pw = P["brg_w"] / 2 + 0.2
    ro = P["housing_od"] / 2
    base = box(xc - P["ped_base_x"] / 2, xc + P["ped_base_x"] / 2, -P["ped_base_y"] / 2, P["ped_base_y"] / 2, zb, zb + P["ped_base_t"])
    tower = prism_yz([(-P["ped_base_y"] / 2 + 5, zb), (P["ped_base_y"] / 2 - 5, zb), (ro, Zs), (-ro, Zs)], xc - th, xc + th)
    body = base.union(tower).union(box(xc - th, xc + th, -ro - 8, ro + 8, Zs - ro, Zs))
    body = body.cut(cyl_x(xc - pw, xc + pw, P["brg_od"] / 2 + 0.1))
    body = body.cut(cyl_x(xc - th - 1, xc + th + 1, P["lip_r"]))
    for s in (-1, 1):                                                   # M4 cap screws into side-entry nut traps
        yb = s * (ro + 2)
        body = body.cut(cyl_z(Zs - 30, Zs + 1, 2.2, xc, yb))
        y_out = s * (ro + 20)
        body = body.cut(box(xc - 4.0, xc + 4.0, min(yb - 4, y_out), max(yb + 4, y_out), Zs - 22, Zs - 18.6))
    xi = xc + th if side == "L" else xc - th                            # pan ledge on the inner face
    xo = xi + 6 if side == "L" else xi - 6
    body = body.union(box(min(xi, xo), max(xi, xo), -30, 30, L["z_pan"] - 6, L["z_pan"]))
    for sx in (-1, 1):
        for sy in (-1, 1):
            body = body.cut(screw_hole_z(xc + sx * 15, sy * 45, zb - 1, zb + P["ped_base_t"] + 1))
    return body


def bearing_cap(xc):
    hw = P["tower_w"] / 2
    pw = P["brg_w"] / 2 + 0.2
    ro = P["housing_od"] / 2
    cap = box(xc - hw, xc + hw, -ro - 8, ro + 8, Zs, Zs + 8).union(
        cyl_x(xc - hw, xc + hw, ro).intersect(box(xc - hw, xc + hw, -ro - 9, ro + 9, Zs, Zs + ro + 1)))
    cap = cap.cut(cyl_x(xc - pw, xc + pw, P["brg_od"] / 2 + 0.1)).cut(cyl_x(xc - hw - 1, xc + hw + 1, P["lip_r"]))
    for s in (-1, 1):
        cap = cap.cut(cyl_z(Zs - 1, Zs + 9, 2.2, xc, s * (ro + 2)))
    return cap


def arbor_pulley():
    """Printed GT2 pulley; the bolt head sits in the hex hub, so the pulley drives the bolt with no set screws."""
    d2 = gt2_pd(L["z_arbor"])
    body = gt2_teeth(L["z_arbor"], *L["x_teeth"])
    fl = d2 / 2 + 2.0
    body = body.union(cyl_x(L["x_teeth"][0] - 1.5, L["x_teeth"][0], fl)).union(cyl_x(L["x_teeth"][1], L["x_teeth"][1] + 1.5, fl))
    body = body.union(cyl_x(*L["x_hex_hub"], 20.0)).union(cyl_x(*L["x_race_hub"], P["brg_race_d"] / 2))
    body = body.cut(cyl_x(L["x_hex_hub"][0] - 1, L["x_race_hub"][1] + 1, (P["bolt_d"] + P["clr_bore"]) / 2))
    return body.cut(hex_x(L["x_hex_hub"][0] - 1, L["x_head_under"], P["head_af"] + 0.4))


def bushing(xa, xb_):
    """1 in wheel bore -> 1/2 in bolt; 1.5 mm shorter than the wheel so the clamp always bears on the wheel."""
    return cyl_x(xa + 0.75, xb_ - 0.75, (P["wheel_bore"] - 0.2) / 2).cut(cyl_x(xa - 1, xb_ + 1, (P["bolt_d"] + P["clr_bore"]) / 2))


def spacer(xa, xb_, face_left=True, face_right=True):
    """Clamp spacer: 40 mm faces where it bears on a wheel or disk, 16 mm where it bears on an inner race."""
    body = cyl_x(xa, xb_, P["brg_race_d"] / 2)
    if face_left:
        body = body.union(cyl_x(xa, xa + 4, P["face_d"] / 2))
    if face_right:
        body = body.union(cyl_x(xb_ - 4, xb_, P["face_d"] / 2))
    if face_left and face_right:
        body = body.union(cyl_x(xa, xb_, 11.0))
    return body.cut(cyl_x(xa - 1, xb_ + 1, (P["bolt_d"] + P["clr_bore"]) / 2))


def _end_plate_profile(y0, y1, zb, zl):
    """YZ outline of a pan end plate: follows the hood's outer arc so no plate rises above the hood.

    Back edge up to the hood's hook tab, then the arc round the top, then a straight run from the
    arc's tangent point down to the top of the front lip."""
    R = P["hood_r"] + P["hood_t"] + 1.0                                 # 1 mm proud of the hood
    dy, dz = y0, zl - Zs
    d = math.hypot(dy, dz)
    phi = math.degrees(math.atan2(dz, dy)) % 360.0 - math.degrees(math.acos(R / d))   # upper tangent point, from +Y
    t_tan = 180.0 - phi                                                 # same point in arc_pts' front-up angle
    return [(y0, zb), (y1, zb), (y1, 178.0), (R, 178.0)] + arc_pts(R, 180.0, t_tan, n=60) + [(y0, zl)]


def pan():
    """Splash pan: sits on the pedestal ledges, tank slides out underneath, U-slots let the arbor lift out."""
    x0, x1 = L["x_wall_L"][0], L["x_wall_R"][1]
    y0, y1 = P["pan_front"], P["pan_back"]
    w, t, zb = P["wall_t"], P["pan_t"], L["z_pan"]
    body = box(x0, x1, y0, y1, zb, zb + t)
    tx0, tx1 = L["x_tank"][0] + P["tank_wall"] + 3, L["x_tank"][1] - P["tank_wall"] - 3
    xs = tx0
    while xs + 5 < tx1:                                                 # drain slots only over the tank's settling side
        body = body.cut(box(xs, xs + 5, y0 + 12, P["weir_y"] - 12, zb - 1, zb + t + 1))
        xs += 11
    for xa, xb_ in ((x0, tx0), (tx1, x1)):                              # ends outside the tank shed toward the slots
        x_hi = xa if xa == x0 else xb_
        body = body.union(prism_xz([(xa, zb + t), (xb_, zb + t), (x_hi, zb + t + 4)], y0, y1))
    body = body.union(prism_yz([(P["weir_y"] - 12, zb + t), (y1 - 3, zb + t), (y1 - 3, zb + t + 6)], x0, x1))
    zl = zb + t + 37                                                    # front lip = arm rest
    body = body.union(box(x0, x1, y0, y0 + 4, zb, zl)).union(cyl_x(x0, x1, 5.0, y0 + 2, zl))
    body = body.union(box(x0, x1, y1 - 3, y1, zb, 175.0))
    zt = Zs + 95                                                        # the arbor slot is cut up to here
    ew = _end_plate_profile(y0, y1, zb, zl)
    for xa, xb_ in ((x0, x0 + w), (x1 - w, x1)):
        body = body.union(prism_yz(ew, xa, xb_))
        body = body.cut(box(xa - 1, xb_ + 1, -P["slot_w"] / 2, P["slot_w"] / 2, Zs, zt + 1).union(cyl_x(xa - 1, xb_ + 1, P["slot_w"] / 2)))
    r_hi, r_lo = P["hood_r"] - 0.3, P["wheel_d"] / 2 + 5.2              # hood rests on two ledges; they stay 5 mm off the wheels
    for xw, sgn in ((x0 + w, 1), (x1 - w, -1)):
        xe = xw + sgn * 4.5
        rib = cyl_x(min(xw, xe), max(xw, xe), r_hi).cut(cyl_x(min(xw, xe) - 1, max(xw, xe) + 1, r_lo))
        body = body.union(rib.intersect(box(min(xw, xe), max(xw, xe), -24.0, -2.0, Zs, Zs + r_hi + 1)))
    for xx in (x0 + 30, x0 + 110):                                      # zip-tie slots for the drip valves
        for zz in (150.0, 165.0):
            body = body.cut(box(xx, xx + 4, y1 - 4, y1 + 1, zz, zz + 3))
    return body


def hood():
    """Shell over the wheels: constant profile (prints standing on end), front drip edge, push-in drip ports."""
    x0, x1 = L["x_wall_L"][1] + 0.5, L["x_wall_R"][0] - 0.5
    r, t = P["hood_r"], P["hood_t"]
    yb = P["pan_back"] - 3
    outer = arc_pts(r + t, P["hood_front_deg"], 180)
    inner = arc_pts(r, P["hood_front_deg"], 180)[::-1]
    shell = prism_yz(outer + [(r + t, 175.0), (r, 175.0)] + inner, x0, x1)
    shell = shell.union(prism_yz([(r, 178.0), (yb + 7, 178.0), (yb + 7, 168.0), (yb + 4.4, 168.0), (yb + 4.4, 175.0), (r, 175.0)], x0, x1))
    tf = math.radians(P["hood_front_deg"])
    yf, zf = -(r + t / 2) * math.cos(tf), Zs + (r + t / 2) * math.sin(tf)
    shell = shell.union(prism_yz([(yf - 1.5, zf), (yf + 1.5, zf), (yf + 1.5, zf - 10), (yf - 1.5, zf - 10)], x0, x1))
    tt = math.radians(105.0)
    d = cq.Vector(0, math.cos(tt), -math.sin(tt))
    for (wa, wb) in L["x_wheels"]:
        p_out = cq.Vector((wa + wb) / 2, -(r + t + 8) * math.cos(tt), Zs + (r + t + 8) * math.sin(tt))
        shell = shell.union(cq.Workplane().add(cq.Solid.makeCylinder(6.0, 12.0, p_out, d)))
        shell = shell.cut(cq.Workplane().add(cq.Solid.makeCylinder(3.15, 30.0, p_out - d * 5, d)))
    return shell


def disk_shroud():
    """Arch round the end disk; open-top slot so it lifts off; tray drains to a cup."""
    xw0, xw1 = L["x_shroud_wall"]
    x1 = L["x_disk_face"] + 14
    r, t = P["shroud_r"], P["shroud_t"]
    zt = Zs - r - 8
    arch = prism_yz(arc_pts(r + t, 10, 180) + [(r + t, zt + 1), (r, zt + 1)] + arc_pts(r, 10, 180)[::-1], xw0, x1)
    tray = prism_yz([(-r - t, zt - 5), (r + t, zt + 3), (r + t, zt), (-r - t, zt - 8)], xw0, x1)
    lip = prism_yz([(-r - t, zt - 8), (-r, zt - 8), (-r, zt + 8), (-r - t, zt + 8)], xw0, x1)
    wall = prism_yz(arc_pts(r + t, 10, 180) + [(r + t, zt), (-r - t, zt - 8), (-r - t, Zs + (r + t) * math.sin(math.radians(10)))], xw0, xw1)
    body = arch.union(tray).union(lip).union(wall)
    body = body.cut(box(xw0 - 1, xw1 + 1, -P["slot_w"] / 2, P["slot_w"] / 2, Zs, Zs + r + t + 1)).cut(cyl_x(xw0 - 1, xw1 + 1, P["slot_w"] / 2))
    for yy in (-r, r - 10):                                             # legs end inside the sloped tray (it rises toward the back)
        z_leg = zt - 8 + 8 * (yy + 10 + r + t) / (2 * (r + t)) + 1.5
        body = body.union(box(xw0, xw0 + 10, yy, yy + 10, P["board_t"], z_leg))
        body = body.union(box(xw0 - 6, xw0 + 16, yy - 6, yy + 16, P["board_t"], P["board_t"] + 4))
        body = body.cut(screw_hole_z(xw0 + 5, yy + 5, P["board_t"] - 1, P["board_t"] + 5))
    xs, ys = (xw1 + x1) / 2, -(r - 10)
    body = body.union(cyl_z(zt - 30, zt - 7, 4.6, xs, ys)).cut(cyl_z(zt - 34, zt - 4, 2.8, xs, ys))
    xp = L["x_disk_face"] - 8
    return body.union(cyl_z(Zs + r, Zs + r + t + 8, 6.0, xp, 15)).cut(cyl_z(Zs + r - 2, Zs + r + t + 10, 3.15, xp, 15))


def backing_plate():
    """6 in backing plate for PSA hook-and-loop pads; clamped by the arbor nut."""
    xh0, xh1 = L["x_disk_hub"]
    xd0, xd1 = L["x_disk"]
    body = cyl_x(xd0, xd1, P["disk_d"] / 2).union(cyl_x(xh0, xh1, 25.0))
    for i in range(8):                                                  # 7 mm ribs like the hub, 14 mm short of the rim: 5.5 mm off the shroud wall
        body = body.union(box(xd0 - P["disk_hub_l"], xd0, -2, 2, 23, P["disk_d"] / 2 - 14).rotate((0, 0, 0), (1, 0, 0), i * 45).translate((0, 0, Zs)))
    return body.cut(cyl_x(xh0 - 1, xd1 + 1, (P["bolt_d"] + P["clr_bore"]) / 2))


def tank():
    """Printed tank with a built-in weir: slurry settles in front, the pump sits in the clean strip at the back."""
    x0, x1 = L["x_tank"]
    y0, y1 = -P["tank_y"] / 2, P["tank_y"] / 2
    z0, z1, w = P["board_t"], L["z_tank_rim"], P["tank_wall"]
    body = box(x0, x1, y0, y1, z0, z1).cut(box(x0 + w, x1 - w, y0 + w, y1 - w, z0 + P["tank_floor"], z1 + 1))
    body = body.union(box(x0 + w, x1 - w, P["weir_y"], P["weir_y"] + w, z0, z0 + P["tank_floor"] + P["weir_h"]))
    body = body.cut(box(x0 + 30, x0 + 46, y1 - w - 1, y1 + 1, z1 - 14, z1 + 1))          # notch for pump tube + wire
    return body.union(box(x0 + 80, x1 - 80, y0 - 12, y0, z1 - 6, z1))                   # front pull lip


def _motor_x():
    x1 = L["x_motor_face"] - 3
    return x1 - min(P["motor_len"] - 10, 50), x1


def motor_cradle():
    """Saddle + slotted base (slide back to tension the belt); the strap clamps the 775 body."""
    x0, x1 = _motor_x()
    ym, zm, r = L["motor_y"], L["z_motor_axis"], P["motor_d"] / 2
    zb = P["board_t"]
    body = box(x0 - 12, x1 + 12, ym - r - 10, ym + r + 10, zb, zb + 6).union(
        box(x0, x1, ym - r - 6, ym + r + 6, zb, zm).cut(cyl_x(x0 - 1, x1 + 1, r + 0.3, ym, zm)))
    for xx in (x0 - 6, x1 + 6):
        body = body.cut(cq.Workplane("XY").center(xx, ym).slot2D(2 * P["motor_slot"] + 4.5, 4.5, 90).extrude(10).translate((0, 0, zb - 1)))
    for xx in (x0 + 8, x1 - 8):
        for s in (-1, 1):
            yy = ym + s * (r + 3)
            body = body.cut(cyl_z(zb + 6, zm + 1, 2.2, xx, yy))
            body = body.cut(box(xx - 4.0, xx + 4.0, yy - 4.0, yy + 4.0, zb + 6, zb + 10))
    return body


def motor_strap():
    x0, x1 = _motor_x()
    ym, zm, r = L["motor_y"], L["z_motor_axis"], P["motor_d"] / 2
    zg = zm + 1.0
    strap = box(x0, x1, ym - r - 6, ym + r + 6, zg, zg + 6).union(
        cyl_x(x0, x1, r + 4, ym, zm).intersect(box(x0, x1, ym - r - 6, ym + r + 6, zg, zm + r + 5)))
    strap = strap.cut(cyl_x(x0 - 1, x1 + 1, r, ym, zm))
    for xx in (x0 + 8, x1 - 8):
        for s in (-1, 1):
            strap = strap.cut(cyl_z(zm - 1, zm + 7, 2.2, xx, ym + s * (r + 3)))
    return strap


def control_mount():
    """Angled plate at the front-left for any PWM speed-control board: zip-tie slots, two wood screws."""
    x0, x1, y0 = -160.0, -80.0, -130.0
    zb = P["board_t"]
    foot = box(x0, x1, y0, y0 + 45, zb, zb + 4)
    plate = prism_yz([(y0, zb), (y0 + 6, zb), (y0 + 45, zb + 70), (y0 + 39, zb + 70)], x0, x1)
    body = foot.union(plate)
    for xx in (x0 + 12, x1 - 16):
        for k in (0.25, 0.75):
            yy, zz = y0 + 3 + 39 * k, zb + 70 * k
            body = body.cut(box(xx, xx + 4, yy - 6, yy + 6, zz - 2, zz + 2))
    for xx in (x0 + 8, x1 - 8):
        body = body.cut(screw_hole_z(xx, y0 + 35, zb - 1, zb + 5))
    return body


# ----------------------------------------------------------------------------------------------
# Bought parts (stand-ins)
# ----------------------------------------------------------------------------------------------
def board():
    return box(P["board_x0"], P["board_x0"] + P["board_l"], -P["board_w"] / 2, P["board_w"] / 2, 0, P["board_t"])


def bolt():
    return hex_x(L["x_head_under"] - P["head_h"], L["x_head_under"], P["head_af"]).union(
        cyl_x(L["x_head_under"], L["x_bolt_tip"], P["bolt_d"] / 2))


def nut():
    return hex_x(*L["x_nut"], 19.05).cut(cyl_x(L["x_nut"][0] - 1, L["x_nut"][1] + 1, P["bolt_d"] / 2))


def washer():
    xa, xb_ = L["x_washer"]
    return cyl_x(xa, xb_, P["washer_od"] / 2).cut(cyl_x(xa - 1, xb_ + 1, P["bolt_d"] / 2))


def bearing(xc):
    return cyl_x(xc - P["brg_w"] / 2, xc + P["brg_w"] / 2, P["brg_od"] / 2).cut(cyl_x(xc - 5, xc + 5, P["bolt_d"] / 2))


def wheel(xa, xb_):
    return cyl_x(xa, xb_, P["wheel_d"] / 2).cut(cyl_x(xa - 1, xb_ + 1, P["wheel_bore"] / 2))


def motor():
    xf, ym, zm = L["x_motor_face"], L["motor_y"], L["z_motor_axis"]
    return cyl_x(xf - P["motor_len"], xf, P["motor_d"] / 2, ym, zm).union(cyl_x(xf, xf + P["motor_shaft_len"], 2.5, ym, zm))


def motor_pulley():
    """Aluminum GT2 20T, 5 mm bore (stock 3D-printer part)."""
    ym, zm = L["motor_y"], L["z_motor_axis"]
    t0, t1 = L["xb"] - 4.0, L["xb"] + 4.0
    od = gt2_pd(P["z_motor"]) - 0.508
    return cyl_x(t0, t1, od / 2, ym, zm).union(cyl_x(t0 - 1, t0, od / 2 + 1.5, ym, zm)).union(
        cyl_x(t1, t1 + 1, od / 2 + 1.5, ym, zm)).union(cyl_x(t0 - 8, t0 - 1, 6.5, ym, zm)).cut(cyl_x(t0 - 9, t1 + 2, 2.5, ym, zm))


def belt():
    from shapely.geometry import Point
    from shapely.ops import unary_union
    r1, r2 = gt2_pd(P["z_motor"]) / 2, gt2_pd(L["z_arbor"]) / 2
    c1, c2 = (L["motor_y"], L["z_motor_axis"]), (0.0, Zs)
    o = unary_union([Point(c1).buffer(r1 + 0.6, 32), Point(c2).buffer(r2 + 0.6, 32)]).convex_hull
    i = unary_union([Point(c1).buffer(r1 - 0.9, 32), Point(c2).buffer(r2 - 0.9, 32)]).convex_hull
    return prism_yz(list(o.exterior.coords)[:-1], L["xb"] - 3, L["xb"] + 3).cut(prism_yz(list(i.exterior.coords)[:-1], L["xb"] - 4, L["xb"] + 4))


def pump():
    x0 = L["x_tank"][0] + 20
    y0 = P["weir_y"] + 8
    return box(x0, x0 + 40, y0, y0 + 32, P["board_t"] + P["tank_floor"], P["board_t"] + P["tank_floor"] + 30)


def pwm_board():
    """Generic PWM speed-control board lying on the mount's sloped face."""
    y0, zb = -130.0, P["board_t"]
    n = (-70.0 / math.hypot(39, 70), 39.0 / math.hypot(39, 70))       # outward normal of the sloped face
    def pt(k, off):
        return (y0 + 39 * k + n[0] * off, zb + 70 * k + n[1] * off)
    return prism_yz([pt(0.2, 0.5), pt(0.8, 0.5), pt(0.8, 4.5), pt(0.2, 4.5)], -150.0, -90.0)


# ----------------------------------------------------------------------------------------------
# Catalog
# ----------------------------------------------------------------------------------------------
def spacer_parts():
    out = [("spacer_A", spacer(*L["x_spA"], face_left=False, face_right=True))]
    out += [("spacer_gap", spacer(*g)) for g in L["x_gaps"]]
    out.append(("spacer_B", spacer(*L["x_spB"], face_left=True, face_right=False)))
    out.append(("spacer_C", spacer(*L["x_spC"], face_left=False, face_right=True)))
    return out


# name -> (builder, qty, face on the bed, note). "-z" = as installed, "+z" = upside down, "-x" = left face down...
PRINTED = {
    "pedestal_L": (lambda: pedestal(L["x_brg_L"], "L"), 1, "-z", "base on bed"),
    "pedestal_R": (lambda: pedestal(L["x_brg_R"], "R"), 1, "-z", "base on bed"),
    "bearing_cap": (lambda: bearing_cap(L["x_brg_L"]), 2, "-z", "mating face on bed"),
    "arbor_pulley": (arbor_pulley, 1, "-x", "hex hub on bed"),
    "bushing": (lambda: bushing(*L["x_wheels"][0]), 4, "-x", "on end"),
    "spacer_A": (lambda: spacer_parts()[0][1], 1, "+x", "wheel face on bed"),
    "spacer_gap": (lambda: spacer(*L["x_gaps"][0]), 3, "-x", "on end"),
    "spacer_B": (lambda: spacer_parts()[-2][1], 1, "-x", "wheel face on bed"),
    "spacer_C": (lambda: spacer_parts()[-1][1], 1, "+x", "disk face on bed"),
    "pan": (pan, 1, "-z", "upright"),
    "hood": (hood, 1, "-x", "stands on one end (X vertical), brim 8 mm"),
    "disk_shroud": (disk_shroud, 1, "-x", "inner wall on bed"),
    "backing_plate": (backing_plate, 1, "+x", "disk face on bed"),
    "tank": (tank, 1, "-z", "floor on bed"),
    "motor_cradle": (motor_cradle, 1, "-z", "base on bed"),
    "motor_strap": (motor_strap, 1, "-z", "flat ends on bed"),
    "control_mount": (control_mount, 1, "-x", "side on bed"),
}

# rotations that put the named face on the bed
ORIENT = {"-z": [], "+z": [("x", 180)], "-x": [("y", -90)], "+x": [("y", 90)], "-y": [("x", 90)], "+y": [("x", -90)]}


def printed_instances():
    out = []
    for name, (fn, qty, _, _) in PRINTED.items():
        if name.startswith("spacer_"):
            continue
        if name == "bearing_cap":
            out += [(name, bearing_cap(L["x_brg_L"])), (name, bearing_cap(L["x_brg_R"]))]
        elif name == "bushing":
            out += [(name, bushing(*w)) for w in L["x_wheels"]]
        else:
            out.append((name, fn()))
    return out + spacer_parts()


def bought_parts():
    parts = [("board", board(), (0.82, 0.68, 0.45)), ("bolt", bolt(), (0.75, 0.75, 0.78)), ("nut", nut(), (0.6, 0.6, 0.62)),
             ("washer", washer(), (0.6, 0.6, 0.62)), ("bearing", bearing(L["x_brg_L"]), (0.4, 0.4, 0.45)),
             ("bearing", bearing(L["x_brg_R"]), (0.4, 0.4, 0.45))]
    parts += [("wheel", wheel(a, b), (0.34, 0.35, 0.38)) for (a, b) in L["x_wheels"]]
    parts += [("belt", belt(), (0.05, 0.05, 0.05)), ("motor", motor(), (0.15, 0.15, 0.18)),
              ("motor_pulley", motor_pulley(), (0.75, 0.75, 0.78)), ("pump", pump(), (0.1, 0.3, 0.7)),
              ("pwm_board", pwm_board(), (0.1, 0.45, 0.2))]
    return parts


PRINT_COLORS = {
    "pedestal_L": (0.93, 0.93, 0.9), "pedestal_R": (0.93, 0.93, 0.9), "bearing_cap": (0.95, 0.55, 0.1),
    "arbor_pulley": (0.95, 0.85, 0.2), "bushing": (0.95, 0.85, 0.2),
    "spacer_A": (0.95, 0.85, 0.2), "spacer_gap": (0.95, 0.85, 0.2), "spacer_B": (0.95, 0.85, 0.2), "spacer_C": (0.95, 0.85, 0.2),
    "pan": (0.55, 0.75, 0.9), "hood": (0.95, 0.55, 0.1), "disk_shroud": (0.95, 0.55, 0.1),
    "backing_plate": (0.95, 0.85, 0.2), "tank": (0.36, 0.40, 0.46), "motor_cradle": (0.3, 0.45, 0.85),
    "motor_strap": (0.3, 0.45, 0.85), "control_mount": (0.3, 0.45, 0.85),
}


def orient_for_print(shape, face):
    s = shape
    for ax, deg in ORIENT[face]:
        s = s.rotate((0, 0, 0), {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[ax], deg)
    bb = s.val().BoundingBox()
    return s.translate((-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))


def main(render=True):
    os.makedirs(OUT_STL, exist_ok=True)
    os.makedirs(OUT_STEP, exist_ok=True)
    for d in (OUT_STL, OUT_STEP):
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))
    table = []
    for name, (fn, qty, face, note) in PRINTED.items():
        shp = fn()
        solid = shp.val()
        assert solid.isValid(), f"{name} is not a valid solid"
        printed = orient_for_print(shp, face)
        bb = printed.val().BoundingBox()
        fits = bb.xlen <= 410 and bb.ylen <= 410 and bb.zlen <= 470
        cq.exporters.export(printed, os.path.join(OUT_STL, f"{name}.stl"), tolerance=0.05, angularTolerance=0.15)
        cq.exporters.export(shp, os.path.join(OUT_STEP, f"{name}.step"))
        table.append(dict(part=name, qty=qty, bed_x=round(bb.xlen, 1), bed_y=round(bb.ylen, 1), height=round(bb.zlen, 1),
                          fits_420_bed=fits, solid_cm3=round(solid.Volume() / 1000.0, 1), orientation=note))
    asm = cq.Assembly(name="cabber")
    for i, (name, shp) in enumerate(printed_instances()):
        asm.add(shp, name=f"{name}_{i}", color=cq.Color(*PRINT_COLORS[name]))
    for i, (name, shp, col) in enumerate(bought_parts()):
        asm.add(shp, name=f"{name}_{i}", color=cq.Color(*col))
    asm.export(os.path.join(OUT_STEP, "cabber_assembly.step"))
    with open(os.path.join(HERE, "print_table.json"), "w", newline="\n") as fh:
        json.dump(dict(parameters=P, layout=L, parts=table), fh, indent=1, default=str)
    for row in table:
        print(row)
    print("stack fits the bolt:", L["stack_ok"], "| thread starts x=%.1f, washer ends x=%.1f, nut ends x=%.1f, tip x=%.1f" % (
        L["x_thread_start"], L["x_washer"][1], L["x_nut"][1], L["x_bolt_tip"]))
    print("GT2 %dT motor : %dT arbor, %d mm loop, center distance %.1f, motor %.1f mm behind the arbor; arbor max %.0f RPM; bearing span %.1f" % (
        P["z_motor"], L["z_arbor"], P["gt2_belt"], L["belt_C"], L["motor_y"], L["arbor_max_rpm"], L["x_brg_R"] - L["x_brg_L"]))
    if render:
        import render_views
        render_views.render_all(printed_instances(), bought_parts(), PRINT_COLORS, OUT_RENDER)


if __name__ == "__main__":
    main(render="--no-render" not in sys.argv)
