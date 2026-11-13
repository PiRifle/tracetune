import json
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Mapping

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree

from ._io import LogoExtractError, read_image, write_text


@dataclass(frozen=True)
class FitParameters:
    tol: float = 1.5
    line_tol: float = 1.2
    smooth_sigma: float = 4.0
    corner_scales: tuple = ((8.0, 45.0), (16.0, 55.0), (32.0, 75.0))
    nms_radius: int = 12
    thin_eps: float = 0.2
    min_area: float = 600.0
    reparam_iters: int = 4
    max_depth: int = 40
    min_run: int = 8
    run_sigma_factor: float = 6.0
    junction_snap: float = 80.0

    def __post_init__(self):
        if self.tol <= 0 or self.line_tol < 0 or self.smooth_sigma < 0:
            raise ValueError("tol must be positive; line_tol and smooth_sigma must be non-negative")
        if self.nms_radius < 0 or self.min_area < 0 or self.min_run < 2:
            raise ValueError("nms_radius and min_area must be non-negative; min_run must be at least 2")
        if self.reparam_iters < 1 or self.max_depth < 0:
            raise ValueError("reparam_iters must be positive and max_depth must be non-negative")

    @classmethod
    def from_dict(cls, values=None):
        if values is None:
            return cls()
        if isinstance(values, cls):
            return values
        if not isinstance(values, Mapping):
            raise ValueError("Fit parameters must be a JSON object")

        aliases = {field.name: field.name for field in fields(cls)}
        aliases.update(
            {
                "TOL": "tol",
                "LINE_TOL": "line_tol",
                "SMOOTH_SIGMA": "smooth_sigma",
                "CORNER_SCALES": "corner_scales",
                "NMS_RADIUS": "nms_radius",
                "THIN_EPS": "thin_eps",
                "MIN_AREA": "min_area",
                "REPARAM_ITERS": "reparam_iters",
                "MAX_DEPTH": "max_depth",
                "MIN_RUN": "min_run",
                "RUN_SIGMA_FACTOR": "run_sigma_factor",
                "JUNCTION_SNAP": "junction_snap",
                "corner_nms_radius": "nms_radius",
                "thinning_epsilon": "thin_eps",
                "min_contour_area": "min_area",
                "reparam_iterations": "reparam_iters",
            }
        )
        normalized = {}
        for key, value in values.items():
            if key not in aliases:
                raise ValueError(f"Unknown fit parameter: {key}")
            normalized[aliases[key]] = value
        if "corner_scales" in normalized:
            normalized["corner_scales"] = tuple(
                tuple(float(item) for item in scale)
                for scale in normalized["corner_scales"]
            )
        return cls(**normalized)

    def as_metadata(self):
        return {
            "TOL": self.tol,
            "LINE_TOL": self.line_tol,
            "SMOOTH_SIGMA": self.smooth_sigma,
            "corner_scales": [list(scale) for scale in self.corner_scales],
            "corner_nms_radius": self.nms_radius,
            "thinning_epsilon": self.thin_eps,
            "min_contour_area": self.min_area,
            "reparam_iterations": self.reparam_iters,
            "max_depth": self.max_depth,
            "min_run": self.min_run,
            "run_sigma_factor": self.run_sigma_factor,
            "junction_snap": self.junction_snap,
        }


def chord_param(points):
    distances = np.hypot(np.diff(points[:, 0]), np.diff(points[:, 1]))
    t = np.concatenate(([0.0], np.cumsum(distances)))
    return t / t[-1] if t[-1] > 0 else t


def arc_positions(points):
    return np.concatenate(
        ([0.0], np.cumsum(np.hypot(np.diff(points[:, 0]), np.diff(points[:, 1]))))
    )


def eval_bezier(control_points, t):
    u = t[:, None]
    basis = np.hstack(
        [(1 - u) ** 3, 3 * u * (1 - u) ** 2, 3 * u * u * (1 - u), u**3]
    )
    return basis @ control_points


def fit_cubic_ls(points, t):
    p0, p3 = points[0], points[-1]
    u = t
    b0 = (1 - u) ** 3
    b1 = 3 * u * (1 - u) ** 2
    b2 = 3 * u * u * (1 - u)
    b3 = u**3
    matrix = np.stack([b1, b2], axis=1)
    rhs = points - (np.outer(b0, p0) + np.outer(b3, p3))
    normal = matrix.T @ matrix
    if abs(np.linalg.det(normal)) < 1e-12:
        vector = (p3 - p0) / 3.0
        return np.array([p0, p0 + vector, p3 - vector, p3])
    solution = np.linalg.solve(normal, matrix.T @ rhs)
    return np.array([p0, solution[0], solution[1], p3])


def polyline_dist(query, points):
    starts, ends = points[:-1], points[1:]
    segments = ends - starts
    denominator = (segments * segments).sum(axis=1)
    denominator[denominator == 0] = 1e-12
    offsets = query[:, None, :] - starts[None, :, :]
    positions = (offsets * segments[None, :, :]).sum(-1) / denominator
    positions = np.clip(positions, 0.0, 1.0)
    projections = starts[None, :, :] + positions[..., None] * segments[None, :, :]
    return np.sqrt(((query[:, None, :] - projections) ** 2).sum(-1)).min(axis=1)


def curve_error(points, control_points):
    sample_count = max(64, 4 * len(points))
    samples = eval_bezier(control_points, np.linspace(0, 1, sample_count))
    forward = float(polyline_dist(samples, points).max())
    backward, _ = cKDTree(samples).query(points)
    worst = int(np.argmax(backward))
    return max(forward, float(backward[worst])), worst


def reparam(points, control_points):
    sample_count = max(200, 8 * len(points))
    grid = np.linspace(0, 1, sample_count)
    indices = cKDTree(eval_bezier(control_points, grid)).query(points)[1]
    t = np.maximum.accumulate(grid[indices])
    return t / t[-1] if t[-1] > 0 else t


def collinear(points, params):
    p0, p1 = points[0], points[-1]
    vector = p1 - p0
    length = np.hypot(*vector)
    if length < 1e-9:
        return True
    offsets = points - p0
    cross = vector[0] * offsets[:, 1] - vector[1] * offsets[:, 0]
    return (np.abs(cross) / length).max() <= params.line_tol


def lowpass_run(points, params):
    count = len(points)
    positions = arc_positions(points)
    if count < params.min_run or positions[-1] < params.run_sigma_factor * params.smooth_sigma:
        return points
    spacing = positions[-1] / (count - 1)
    sigma_samples = params.smooth_sigma / max(spacing, 1e-6)
    smooth = np.empty_like(points)
    for channel in range(2):
        smooth[:, channel] = gaussian_filter1d(
            points[:, channel], sigma_samples, mode="reflect"
        )
    smooth[0], smooth[-1] = points[0], points[-1]
    return smooth


def fit_run(points, params, depth=0):
    count = len(points)
    if count <= 3 or collinear(points, params):
        return [("L", points[-1])]
    t = chord_param(points)
    best = None
    for _ in range(params.reparam_iters):
        control_points = fit_cubic_ls(points, t)
        error, worst = curve_error(points, control_points)
        if best is None or error < best[0]:
            best = (error, control_points, worst)
        if error <= params.tol:
            return [("C", control_points)]
        updated = reparam(points, control_points)
        if np.allclose(updated, t):
            break
        t = updated
    _, control_points, worst = best
    if depth >= params.max_depth:
        return [("C", control_points)]
    middle = worst if 2 <= worst <= count - 3 else count // 2
    return fit_run(points[: middle + 1], params, depth + 1) + fit_run(
        points[middle:], params, depth + 1
    )


def find_corners(points, params):
    count = len(points)
    closed = np.vstack([points, points[0]])
    positions = arc_positions(closed)
    total = positions[-1]
    score = np.zeros(count)
    for window, threshold in params.corner_scales:
        for i in range(count):
            before, after = positions[i] - window, positions[i] + window
            back_index = (
                np.searchsorted(positions, before)
                if before >= 0
                else np.searchsorted(positions, total + before)
            )
            forward_index = (
                np.searchsorted(positions, after)
                if after <= total
                else np.searchsorted(positions, after - total)
            )
            back_index = min(max(int(back_index), 0), count - 1)
            forward_index = min(max(int(forward_index), 0), count - 1)
            v1 = points[i] - points[back_index]
            v2 = points[forward_index] - points[i]
            n1, n2 = np.hypot(*v1), np.hypot(*v2)
            if n1 < 1e-6 or n2 < 1e-6:
                continue
            turn = np.degrees(
                np.arccos(np.clip(np.dot(v1, v2) / (n1 * n2), -1, 1))
            )
            if turn > threshold:
                score[i] = max(score[i], turn)
    candidates = np.where(score > 0)[0]
    keep, suppressed = [], np.zeros(count, bool)
    for i in candidates[np.argsort(-score[candidates])]:
        if suppressed[i]:
            continue
        keep.append(i)
        for offset in range(-params.nms_radius, params.nms_radius + 1):
            suppressed[(i + offset) % count] = True
    return sorted(keep)


def line_intersection(p1, p2, p3, p4):
    denominator = (p2[0] - p1[0]) * (p4[1] - p3[1]) - (p2[1] - p1[1]) * (
        p4[0] - p3[0]
    )
    if abs(denominator) < 1e-9:
        return None
    t = (
        (p3[0] - p1[0]) * (p4[1] - p3[1])
        - (p3[1] - p1[1]) * (p4[0] - p3[0])
    ) / denominator
    return p1 + t * (p2 - p1)


def snap_straight_junctions(segments, params):
    previous = None
    output = []
    i = 0
    while i < len(segments):
        kind, start, end = segments[i]
        if (
            kind == "L"
            and previous is not None
            and i + 1 < len(segments)
            and segments[i + 1][0] == "L"
        ):
            next_end = segments[i + 1][2]
            intersection = line_intersection(start, end, end, next_end)
            if intersection is not None and np.hypot(*(intersection - end)) < params.junction_snap:
                output.append(("L", start, intersection))
                segments[i + 1] = ("L", intersection, next_end)
                previous = intersection
                i += 1
                continue
        output.append((kind, start, end))
        previous = end
        i += 1
    return output


def contour_to_path(points, params):
    points = points.astype(float)
    corners = find_corners(points, params)
    if not corners:
        runs = [np.vstack([points, points[0]])]
    else:
        runs = []
        for start, end in zip(corners, corners[1:] + [corners[0]]):
            runs.append(
                points[start : end + 1]
                if end > start
                else np.vstack([points[start:], points[: end + 1]])
            )

    segments = []
    current = runs[0][0]
    for run in runs:
        if not collinear(run, params):
            run = lowpass_run(run, params)
            approx = cv2.approxPolyDP(
                run.reshape(-1, 1, 2).astype(np.float32), params.thin_eps, False
            )
            run = approx[:, 0, :].astype(float)
        for kind, data in fit_run(run, params):
            if kind == "L":
                segments.append(("L", current, np.array(data, float)))
                current = np.array(data, float)
            else:
                segments.append(("C", current, data))
                current = data[3]
    segments = snap_straight_junctions(segments, params)
    line_count = sum(1 for kind, _, _ in segments if kind == "L")
    cubic_count = len(segments) - line_count
    parts = [f"M{runs[0][0][0]:.2f},{runs[0][0][1]:.2f}"]
    for kind, _, data in segments:
        if kind == "L":
            parts.append(f"L{data[0]:.2f},{data[1]:.2f}")
        else:
            parts.append(
                f"C{data[1][0]:.2f},{data[1][1]:.2f} "
                f"{data[2][0]:.2f},{data[2][1]:.2f} "
                f"{data[3][0]:.2f},{data[3][1]:.2f}"
            )
    parts.append("Z")
    return "".join(parts), line_count, cubic_count, len(corners)


def vectorize_mask(mask_path, out_svg, out_meta=None, params=None):
    params = FitParameters.from_dict(params)
    mask_path = Path(mask_path)
    out_svg = Path(out_svg)
    out_meta = Path(out_meta) if out_meta else out_svg.with_suffix(".meta.json")
    mask = read_image(mask_path)
    contours, _ = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)

    paths, total_lines, total_cubics, total_corners = [], 0, 0, 0
    for contour in contours:
        if cv2.contourArea(contour) < params.min_area:
            continue
        path, lines, cubics, corners = contour_to_path(contour[:, 0, :], params)
        paths.append(path)
        total_lines += lines
        total_cubics += cubics
        total_corners += corners
    if not paths:
        raise LogoExtractError(
            f"No contours met the minimum area of {params.min_area} pixels"
        )

    height, width = mask.shape
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'
        f'<path d="{" ".join(paths)}" fill="#000000" fill-rule="evenodd"/>\n</svg>\n'
    )
    write_text(out_svg, svg)
    stats = {
        "contours": len(paths),
        "corners": total_corners,
        "line_segments": total_lines,
        "cubic_segments": total_cubics,
        "viewbox": [width, height],
    }
    metadata = {
        "source_mask": str(mask_path),
        "output_svg": str(out_svg),
        "parameters": params.as_metadata(),
        "stats": stats,
    }
    write_text(out_meta, json.dumps(metadata, indent=2) + "\n")
    return stats
