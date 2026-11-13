import math
from dataclasses import replace
from pathlib import Path

from .compare import compare_svg
from .fit import FitParameters, vectorize_mask

PRESETS = {
    "compact": {
        "quality": 0,
        "description": "Fewer segments and a smaller SVG",
        "tol": 11.0,
        "line_tol": 2.5,
        "smooth_sigma": 10.0,
    },
    "balanced": {
        "quality": 65,
        "description": "A practical balance of fidelity and size",
        "tol": 4.0,
        "line_tol": 1.8,
        "smooth_sigma": 7.0,
    },
    "detailed": {
        "quality": 100,
        "description": "Maximum detail with more segments",
        "tol": 1.5,
        "line_tol": 1.2,
        "smooth_sigma": 4.0,
    },
}


def preset_parameters(name):
    if name not in PRESETS:
        raise ValueError(f"Unknown preset {name!r}; choose from {', '.join(PRESETS)}")
    values = PRESETS[name]
    return FitParameters(
        tol=values["tol"],
        line_tol=values["line_tol"],
        smooth_sigma=values["smooth_sigma"],
    )


def quality_parameters(quality):
    quality = float(quality)
    if not math.isfinite(quality) or not 0 <= quality <= 100:
        raise ValueError("quality must be between 0 and 100")
    anchors = [PRESETS[name] for name in ("compact", "balanced", "detailed")]
    lower, upper = anchors[0], anchors[-1]
    for left, right in zip(anchors, anchors[1:]):
        if left["quality"] <= quality <= right["quality"]:
            lower, upper = left, right
            break
    span = upper["quality"] - lower["quality"]
    amount = (quality - lower["quality"]) / span if span else 0
    values = {
        key: round(lower[key] + amount * (upper[key] - lower[key]), 3)
        for key in ("tol", "line_tol", "smooth_sigma")
    }
    return FitParameters(**values)


def list_presets():
    return [
        {
            "name": name,
            "quality": values["quality"],
            "description": values["description"],
            "tol": values["tol"],
            "line_tol": values["line_tol"],
            "smooth_sigma": values["smooth_sigma"],
        }
        for name, values in PRESETS.items()
    ]


def optimize_mask(
    mask_path,
    out_svg,
    *,
    quality=None,
    preset=None,
    min_area=None,
    render_path=None,
    diff_path=None,
):
    if quality is not None and preset is not None:
        raise ValueError("Choose either quality or preset, not both")
    if quality is not None:
        params = quality_parameters(quality)
        selection = {"quality": float(quality), "preset": None}
    else:
        preset = preset or "balanced"
        params = preset_parameters(preset)
        selection = {"quality": PRESETS[preset]["quality"], "preset": preset}
    if min_area is not None:
        params = replace(params, min_area=min_area)

    out_svg = Path(out_svg)
    render_path = Path(render_path) if render_path else out_svg.with_suffix(".png")
    diff_path = Path(diff_path) if diff_path else out_svg.with_suffix(".diff.png")
    stats = vectorize_mask(mask_path, out_svg, params=params)
    comparison = compare_svg(mask_path, out_svg, diff_path, render_path)
    return {
        **selection,
        "output": str(out_svg),
        "metadata": str(out_svg.with_suffix(".meta.json")),
        "render": str(render_path),
        "diff": str(diff_path),
        "parameters": {
            "tol": params.tol,
            "line_tol": params.line_tol,
            "smooth_sigma": params.smooth_sigma,
            "min_area": params.min_area,
        },
        "stats": stats,
        "comparison": comparison,
    }
