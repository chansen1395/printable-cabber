"""Interference and clearance check of the whole assembly.

    python cad/check_clashes.py

What it does, and why it can be trusted:

1. Inventory. Every body that the STEP assembly and the renders use (printed_instances() and
   bought_parts() in cabber.py: printed parts, stand-ins, the base board, wheels, belt, motor, pump and
   so on) must be one valid solid, the printed counts must match the PRINTED table, and the exported
   STEP assembly must hold the same solids with the same total volume. The STLs must be current,
   watertight and fit the bed, and the bolt stack must fit the bolt.
2. Interference, two independent ways. Every pair of bodies whose boxes overlap is intersected (a) with
   OpenCascade's exact boolean and (b) on tessellated meshes with manifold3d. A boolean that errors
   out, an invalid result, an empty body, or the two engines disagreeing is a failure, never a silent
   "no overlap".
3. Clearance. Moving parts must keep a running gap to everything they do not belong with: wheels and
   end disk 5 mm, other rotating parts 1 mm, the belt 2 mm, the sliding tank 3 mm. The minimum gap
   of every moving part and its nearest neighbor is printed.
4. Self-test. Before it judges the model it makes mistakes on purpose (hood dropped into the wheels,
   a wheel pushed at the pan, an empty body) and checks that each one is caught.

Exit status: 0 all clear, 1 problems found, 2 the check itself could not run. No arguments.
"""
import itertools
import os
import sys

import cadquery as cq
import manifold3d as m3
import numpy as np
import trimesh
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cabber  # noqa: E402

# ---- tolerances -------------------------------------------------------------------------------
OCC_TOL = 1.0         # mm^3: the exact boolean may report this much for faces that merely touch
MESH_TOL = 60.0       # mm^3: tessellation error on touching cylinders (coincident bores) stays well below this
MESH_LINEAR = 0.03    # mm, tessellation deviation for the mesh engine
# overlaps that are intended: the belt's teeth sit in the pulley grooves (modeled as a 0.65 mm overlap)
ALLOWED_OVERLAP = {frozenset(("belt", "arbor_pulley")): 150.0, frozenset(("belt", "motor_pulley")): 150.0}

# ---- what moves (design knowledge) ---------------------------------------------------------------
ROTOR = {"bolt", "nut", "washer", "arbor_pulley", "bushing", "spacer_A", "spacer_gap", "spacer_B", "spacer_C",
         "wheel", "backing_plate"}                                  # all of these turn with the arbor
WORKING = {"wheel", "backing_plate"}                                # the abrasive faces
DRIVE = {"belt", "motor_pulley"}
SLIDER = {"tank"}                                                   # slides out the front for emptying
MOVING = ROTOR | DRIVE | SLIDER
# touching is by design for these pairs: inner race on the arbor, belt on the pulleys, tank on its bench
TOUCH_OK = (
    [frozenset(("bearing", n)) for n in ("bolt", "arbor_pulley", "spacer_A", "spacer_B", "spacer_C")]
    + [frozenset(p) for p in (("belt", "arbor_pulley"), ("belt", "motor_pulley"), ("motor", "motor_pulley"),
                              ("tank", "board"), ("tank", "pump"))]
)


def required_gap(a, b):
    """Minimum running clearance (mm) for a pair of body names, or None if the pair never moves relative to each other."""
    if frozenset((a, b)) in TOUCH_OK:
        return None
    if (a in ROTOR and b in ROTOR) or (a in DRIVE and b in DRIVE) or (a in ROTOR and b in DRIVE) or (a in DRIVE and b in ROTOR):
        return None                                                 # one rigid body, or the belt bearing on the pulleys
    if a in WORKING or b in WORKING:
        return 5.0
    if a in SLIDER or b in SLIDER:
        return 3.0
    if a == "belt" or b == "belt":
        return 2.0
    if a in MOVING or b in MOVING:
        return 1.0
    return None


class CheckError(RuntimeError):
    """The check itself could not be completed. Never treated as 'no clash'."""


# ---- bodies ----------------------------------------------------------------------------------------
def bodies():
    items = [(n, s.val()) for n, s in cabber.printed_instances()] + [(n, s.val()) for n, s, _ in cabber.bought_parts()]
    total, seen, out = {}, {}, []
    for n, _ in items:
        total[n] = total.get(n, 0) + 1
    for n, shp in items:
        seen[n] = seen.get(n, 0) + 1
        out.append(dict(name=n, label=n if total[n] == 1 else f"{n}#{seen[n]}", shape=shp, man=None))
    return out


def inventory(bs):
    problems = []
    for b in bs:
        shp = b["shape"]
        if not shp.isValid():
            problems.append(f"{b['label']}: invalid solid")
        n_solids = len(shp.Solids())
        if n_solids != 1:
            problems.append(f"{b['label']}: {n_solids} separate solids (a floating fragment, or a gap inside the part)")
        if shp.Volume() <= 0:
            problems.append(f"{b['label']}: no volume")
    counts = {}
    for b in bs:
        counts[b["name"]] = counts.get(b["name"], 0) + 1
    bought = {n for n, _, _ in cabber.bought_parts()}
    for name, (_, qty, _, _) in cabber.PRINTED.items():
        if counts.get(name, 0) != qty:
            problems.append(f"{name}: {counts.get(name, 0)} in the assembly, {qty} in the print list")
    for name in counts:
        if name not in cabber.PRINTED and name not in bought:
            problems.append(f"{name}: unknown body (not in PRINTED or the bought list)")
    problems += print_files(bs)
    if not cabber.L["stack_ok"]:
        problems.append("bolt stack: the nut does not fit on the bolt (see cabber.py output)")
    step = os.path.join(HERE, "step", "cabber_assembly.step")
    if os.path.exists(step):                                        # the exported assembly must hold exactly these solids
        asm = cq.importers.importStep(step)
        solids = [s for v in asm.vals() for s in v.Solids()]
        vol_step, vol_here = sum(s.Volume() for s in solids), sum(b["shape"].Volume() for b in bs)
        if len(solids) != len(bs) or abs(vol_step - vol_here) > 1e-4 * vol_here:
            problems.append(f"STEP assembly has {len(solids)} solids / {vol_step:.0f} mm^3 but the model has "
                            f"{len(bs)} / {vol_here:.0f}: re-run cabber.py")
    else:
        problems.append("cad/step/cabber_assembly.step is missing: run cabber.py first")
    return problems


def print_files(bs):
    """Every printed part has a current, watertight STL that fits the bed (420 x 420 mm bed, 10 mm margin)."""
    problems, vol = [], {b["name"]: b["shape"].Volume() for b in bs}
    for name in cabber.PRINTED:
        path = os.path.join(HERE, "stl", f"{name}.stl")
        if not os.path.exists(path):
            problems.append(f"{name}.stl is missing: run cabber.py")
            continue
        mesh = trimesh.load(path)
        if not (mesh.is_watertight and mesh.is_winding_consistent):
            problems.append(f"{name}.stl is not watertight")
        if abs(mesh.volume - vol[name]) > 0.015 * vol[name]:
            problems.append(f"{name}.stl is stale ({mesh.volume:.0f} mm^3 against {vol[name]:.0f} in the model): run cabber.py")
        ex = mesh.extents
        if ex[0] > 410 or ex[1] > 410 or ex[2] > 470:
            problems.append(f"{name}.stl does not fit the bed ({ex[0]:.0f} x {ex[1]:.0f} x {ex[2]:.0f} mm)")
    return problems


# ---- the two interference engines ----------------------------------------------------------------------
def occ_overlap(a, b):
    """Exact B-rep intersection volume in mm^3. Raises if OpenCascade could not do it."""
    if a.Volume() <= 0 or b.Volume() <= 0:
        raise CheckError("empty body passed to the boolean")
    op = BRepAlgoAPI_Common(a.wrapped, b.wrapped)
    if not op.IsDone():
        raise CheckError("OpenCascade boolean failed")
    res = cq.Shape.cast(op.Shape())
    if not res.isValid():
        raise CheckError("OpenCascade boolean returned an invalid shape")
    return res.Volume()


def to_manifold(shape):
    verts, faces = shape.tessellate(MESH_LINEAR, 0.2)
    if not len(faces):
        raise CheckError("empty tessellation")
    mesh = trimesh.Trimesh(np.array([(p.x, p.y, p.z) for p in verts]), np.array(faces), process=True)
    if not mesh.is_watertight:
        raise CheckError("a tessellated body is not watertight")
    man = m3.Manifold(m3.Mesh(vert_properties=np.array(mesh.vertices, dtype=np.float32),
                              tri_verts=np.array(mesh.faces, dtype=np.uint32)))
    if man.status() != m3.Error.NoError:
        raise CheckError(f"manifold3d rejected a mesh: {man.status()}")
    return man


def manifold_of(b):
    if b["man"] is None:
        b["man"] = to_manifold(b["shape"])
    return b["man"]


def mesh_overlap(ma, mb):
    return (ma ^ mb).volume()                                       # in manifold3d, ^ is intersection


def judge_overlap(name_a, name_b, occ, mesh):
    """Problem strings for one pair, given both engines' overlap volumes."""
    cap = ALLOWED_OVERLAP.get(frozenset((name_a, name_b)))
    if cap is not None:
        return [] if max(occ, mesh) <= cap else [f"intended overlap too deep ({occ:.0f} / {mesh:.0f} mm^3, limit {cap:.0f})"]
    out = []
    if occ > OCC_TOL:
        out.append(f"CLASH {occ:.1f} mm^3 (exact) / {mesh:.1f} mm^3 (mesh)")
    elif mesh > MESH_TOL:
        out.append(f"ENGINES DISAGREE: mesh says {mesh:.1f} mm^3, the exact boolean says {occ:.2f}")
    if occ > 300 and mesh < 0.1 * occ:
        out.append(f"ENGINES DISAGREE: exact {occ:.0f} mm^3, mesh {mesh:.0f}")
    return out


def bbox_gap(a, b):
    ba, bb = a.BoundingBox(), b.BoundingBox()
    return max(bb.xmin - ba.xmax, ba.xmin - bb.xmax, bb.ymin - ba.ymax, ba.ymin - bb.ymax, bb.zmin - ba.zmax, ba.zmin - bb.zmax)


# ---- the full pass ------------------------------------------------------------------------------------
def analyze(bs):
    problems, gaps, n_pairs = [], {}, 0
    for a, b in itertools.combinations(bs, 2):
        if bbox_gap(a["shape"], b["shape"]) > 25:
            continue
        if bbox_gap(a["shape"], b["shape"]) <= 0:                   # boxes overlap: intersect both ways
            n_pairs += 1
            occ = occ_overlap(a["shape"], b["shape"])
            mesh = mesh_overlap(manifold_of(a), manifold_of(b))
            for msg in judge_overlap(a["name"], b["name"], occ, mesh):
                problems.append(f"{a['label']} x {b['label']}: {msg}")
        req = required_gap(a["name"], b["name"])
        if req is not None:
            d = a["shape"].distance(b["shape"])
            for me, other in ((a, b), (b, a)):
                if me["name"] in MOVING and (me["label"] not in gaps or d < gaps[me["label"]][0]):
                    gaps[me["label"]] = (d, other["label"], req)
            if d < req - 1e-6:
                problems.append(f"{a['label']} to {b['label']}: gap {d:.2f} mm, needs {req:.1f}")
    print(f"bodies: {len(bs)}   pairs with overlapping boxes intersected two ways: {n_pairs}")
    print("\nminimum clearance of each moving part to the nearest neighbor (mm)")
    for label, (d, other, req) in sorted(gaps.items(), key=lambda kv: (kv[1][0] - kv[1][2], kv[0])):
        print(f"  {label:<16} {other:<16} {d:6.2f}   needs {req:3.1f}   {'ok' if d >= req - 1e-6 else 'TOO CLOSE'}")
    return problems


# ---- self-test: the checker must catch the mistakes it is meant to catch ----------------------------------
def selftest(bs):
    by = {b["label"]: b for b in bs}
    fails = []
    hood = by["hood"]["shape"].translate(cq.Vector(0, 0, -30))      # 1. hood dropped 30 mm into the wheels
    wheel = by["wheel#2"]
    occ, mesh = occ_overlap(hood, wheel["shape"]), mesh_overlap(to_manifold(hood), manifold_of(wheel))
    if not (occ > 1000 and mesh > 1000 and judge_overlap("hood", "wheel", occ, mesh)):
        fails.append(f"dropped hood not caught (exact {occ:.0f}, mesh {mesh:.0f})")
    w1 = by["wheel#1"]["shape"].translate(cq.Vector(-3.3, 0, 0))    # 2. wheel pushed to 2 mm from the pan, no overlap
    d = w1.distance(by["pan"]["shape"])
    if not (d < required_gap("wheel", "pan")):
        fails.append(f"wheel near the pan not caught (gap {d:.2f})")
    try:                                                            # 3. an impossible boolean must raise, not return 0
        occ_overlap(cq.Compound.makeCompound([]), wheel["shape"])
        fails.append("empty body did not raise")
    except CheckError:
        pass
    solids = cq.Workplane("XY").box(5, 5, 5).union(cq.Workplane("XY").box(5, 5, 5).translate((20, 0, 0))).val()
    if len(solids.Solids()) != 2:                                   # 4. the fragment test sees a second solid
        fails.append("two-solid control did not have two solids")
    return fails


def main():
    bs = bodies()
    problems = inventory(bs)
    if not problems:
        print(f"inventory: {len(bs)} bodies, each one valid solid; counts match the print list; STEP assembly matches; "
              f"{len(cabber.PRINTED)} STLs current, watertight, fit the bed; bolt stack fits")
    fails = selftest(bs)
    print("self-test:", "ok (dropped hood, wheel near the pan and an empty body are all caught)" if not fails else fails)
    problems += analyze(bs)
    problems += [f"self-test: {f}" for f in fails]
    print()
    for p in problems:
        print("FAIL", p)
    print("clash check:", "none; clearances ok" if not problems else f"{len(problems)} problem(s)")
    return problems


if __name__ == "__main__":
    try:
        sys.exit(1 if main() else 0)
    except CheckError as exc:
        print("CHECK COULD NOT RUN:", exc)
        sys.exit(2)
