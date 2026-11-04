"""Offscreen renders of the cabber assembly with VTK (through pyvista).

A real z-buffer draws the parts, so nothing can show through anything else unless the solids
really overlap.

Meshes are smooth-shaded (vertex normals are averaged across faces that meet at less than
FEATURE_ANGLE degrees, so cylinders look round and box edges stay crisp) and each image is drawn
at SUPERSAMPLE x and averaged down for anti-aliasing. Needs: pip install pyvista (VTK comes with it).

    scene(printed, bought, colors)                       -> meshes for every body
    render_all(printed, bought, colors, out_dir)         the six documentation views plus portfolio_assembly.png
    render_portfolio(meshes, path)                        the 1800 x 1200 hero image, white background
"""
import os

import numpy as np
import pyvista as pv
from PIL import Image

pv.OFF_SCREEN = True

FEATURE_ANGLE = 35.0
SUPERSAMPLE = 2
# screen-space ambient occlusion: darkens creases and contact lines. bias must be large (mm scene) or flat faces band.
SSAO = dict(radius=20, bias=5.0, kernel_size=64, blur=True)

# exploded-view offsets per part name (mm)
EXPLODE = {
    "hood": (0, 0, 170), "bearing_cap": (0, 0, 90), "disk_shroud": (110, 0, 40), "backing_plate": (170, 0, 0),
    "washer": (190, 0, 0), "nut": (205, 0, 0), "tank": (0, -330, -10), "pump": (0, -330, 60), "pan": (0, 0, 50),
    "motor_cradle": (-60, 60, 0), "motor_strap": (-60, 60, 80), "motor": (-60, 60, 40), "motor_pulley": (-60, 60, 40),
    "belt": (-40, 0, 40), "arbor_pulley": (-60, 0, 120), "bolt": (-120, 0, 120), "bearing": (0, 0, 120),
    "wheel": (0, 0, 120), "bushing": (0, 0, 120), "spacer_A": (0, 0, 120), "spacer_gap": (0, 0, 120),
    "spacer_B": (0, 0, 120), "spacer_C": (0, 0, 120), "control_mount": (-40, -60, 0), "pwm_board": (-40, -100, 40),
}

# view directions: focal point -> camera. X is along the arbor (disk end at +X), Y is back, Z is up.
VIEWS = {
    "iso": (0.55, -0.80, 0.50),        # front, from the disk side, above
    "front": (0.0, -1.0, 0.04),        # operator side
    "back": (-0.55, 0.80, 0.42),
    "left": (-1.0, 0.0, 0.10),         # drive end
    "hood_off": (0.50, -0.75, 0.62),
}


def mesh_of(shape, tol=0.05, ang=0.12):
    """CadQuery shape -> smooth-shaded pyvista mesh (shared vertices, sharp edges kept)."""
    verts, faces = shape.val().tessellate(tol, ang)
    v = np.array([(p.x, p.y, p.z) for p in verts])
    f = np.array(faces)
    cells = np.hstack([np.full((len(f), 1), 3), f]).ravel()
    m = pv.PolyData(v, cells).clean(tolerance=1e-6)
    return m.compute_normals(cell_normals=False, point_normals=True, split_vertices=True,
                             feature_angle=FEATURE_ANGLE, auto_orient_normals=False)


def scene(printed, bought, colors):
    """[(name, mesh, color)] for every body in the assembly."""
    items = [(n, s, colors[n]) for n, s in printed] + list(bought)
    return [(n, mesh_of(s), c) for n, s, c in items]


def _exploded(meshes):
    return [(n, m.translate(EXPLODE.get(n, (0, 0, 0)), inplace=False), c) for n, m, c in meshes]


def _fit(cam, pts, aspect, fill, shift):
    """Center the projected silhouette and dolly the (perspective) camera until it spans `fill` of the frame."""
    pos, foc, up = np.array(cam.position), np.array(cam.focal_point), np.array(cam.up)
    fwd = foc - pos
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, up)
    right /= np.linalg.norm(right)
    upv = np.cross(right, fwd)
    tan_v = np.tan(np.radians(cam.view_angle / 2))
    dist = np.linalg.norm(foc - pos)
    for _ in range(8):
        rel = pts - pos
        z = rel @ fwd
        x = (rel @ right) / z / (tan_v * aspect)        # -1..1 across the frame width
        y = (rel @ upv) / z / tan_v                     # -1..1 across the frame height
        cx, cy = (x.min() + x.max()) / 2, (y.min() + y.max()) / 2
        half = max((x.max() - x.min()) / 2 * 1.0, (y.max() - y.min()) / 2 * 1.0)
        step = right * cx * tan_v * aspect * dist + upv * cy * tan_v * dist
        pos, foc = pos + step, foc + step
        dist *= half / fill
        pos = foc - fwd * dist
    step = right * shift[0] * dist * tan_v * aspect + upv * shift[1] * dist * tan_v
    cam.position, cam.focal_point = tuple(pos + step), tuple(foc + step)


def draw(meshes, path, direction, size=(1440, 960), fill=0.88, view_angle=22.0, ssao=SSAO, shadows=False, shift=(0.0, 0.0), fit_box=None):
    """Render `meshes` seen from `direction` (focal point -> camera) into a PNG of `size` pixels.

    fit_box=((x0, y0, z0), (x1, y1, z1)) zooms on a region instead of fitting the whole scene (for close-ups)."""
    w, h = size[0] * SUPERSAMPLE, size[1] * SUPERSAMPLE
    pl = pv.Plotter(off_screen=True, window_size=(w, h))
    pl.set_background("white")
    for _, m, c in meshes:
        pl.add_mesh(m, color=c, smooth_shading=True, ambient=0.22, diffuse=0.78, specular=0.18, specular_power=24)
    pts = np.vstack([m.points for _, m, _ in meshes])
    if fit_box is not None:
        (x0, y0, z0), (x1, y1, z1) = fit_box
        pts = np.array([(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)], float)
    lo, hi = pts.min(0), pts.max(0)
    focus = (lo + hi) / 2
    d = np.array(direction, float)
    d /= np.linalg.norm(d)
    cam = pl.camera
    cam.view_angle = view_angle
    cam.focal_point = tuple(focus)
    cam.position = tuple(focus + d * np.linalg.norm(hi - lo) * 2.0)
    cam.up = (0, 0, 1)
    _fit(cam, pts, size[0] / size[1], fill, shift)
    pl.reset_camera_clipping_range()
    pl.enable_lightkit()
    if ssao:
        pl.enable_ssao(**ssao)
    if shadows:
        pl.enable_shadows()
    img = pl.screenshot(return_img=True)
    pl.close()
    Image.fromarray(img[..., :3]).resize(size, Image.LANCZOS).save(path)
    return path


def render_all(printed, bought, colors, out_dir):
    """The six documentation views. Returns the meshes so a caller can reuse them."""
    os.makedirs(out_dir, exist_ok=True)
    meshes = scene(printed, bought, colors)
    out = lambda n: os.path.join(out_dir, f"assembly_{n}.png")  # noqa: E731
    draw(meshes, out("iso"), VIEWS["iso"])
    draw(meshes, out("front"), VIEWS["front"], view_angle=8.0)
    draw(meshes, out("back"), VIEWS["back"])
    draw(meshes, out("left"), VIEWS["left"], view_angle=8.0)
    draw(_exploded(meshes), out("exploded"), VIEWS["iso"])
    draw([t for t in meshes if t[0] != "hood"], out("hood_off"), VIEWS["hood_off"])
    render_portfolio(meshes, os.path.join(out_dir, "portfolio_assembly.png"))
    return meshes


def view_dir(azimuth, elevation):
    """Unit vector from the machine to the camera. Azimuth 0 = straight at the operator side, positive toward the disk end."""
    a, e = np.radians(azimuth), np.radians(elevation)
    return (np.sin(a) * np.cos(e), -np.cos(a) * np.cos(e), np.sin(e))


def render_portfolio(meshes, path, azimuth=36.0, elevation=18.0, fill=0.93):
    """The hero image: assembled, hood on, three-quarter view, 1800 x 1200 (3:2), white background, no text."""
    return draw(meshes, path, view_dir(azimuth, elevation), size=(1800, 1200), fill=fill, view_angle=20.0)
