import json
from pathlib import Path

import cv2
import numpy as np

from ._io import LogoExtractError, read_image, write_image, write_text
from .compare import compare_svg, render_svg
from .fit import FitParameters, vectorize_mask


def candidate_path(directory, name, suffix):
    if not name or Path(name).name != name or name in {".", ".."}:
        raise ValueError(f"Invalid candidate name: {name!r}")
    return Path(directory) / f"{name}{suffix}"


def evaluate(mask_path, output_dir, name, values, preview_width=900):
    if preview_width <= 0:
        raise ValueError("preview_width must be greater than zero")
    params = FitParameters.from_dict(values)
    svg = candidate_path(output_dir, name, ".svg")
    meta = candidate_path(output_dir, name, ".meta.json")
    stats = vectorize_mask(mask_path, svg, meta, params)

    full = candidate_path(output_dir, name, "_full.png")
    render_svg(svg, full)
    diff = candidate_path(output_dir, name, "_diff.png")
    comparison = compare_svg(mask_path, svg, diff, render_path=full)

    rendered = read_image(full, cv2.IMREAD_COLOR)
    scale = preview_width / rendered.shape[1]
    preview_image = cv2.resize(
        rendered, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA
    )
    preview = candidate_path(output_dir, name, "_preview.png")
    write_image(preview, preview_image)
    diff_image = read_image(diff, cv2.IMREAD_COLOR)
    diff_image = cv2.resize(
        diff_image,
        (preview_image.shape[1], preview_image.shape[0]),
        interpolation=cv2.INTER_AREA,
    )
    write_image(diff, diff_image)

    return {
        "name": name,
        "disagreement_pct": comparison["disagreement_pct"],
        "missing_px": comparison["missing_px"],
        "extra_px": comparison["extra_px"],
        "lines": stats["line_segments"],
        "cubics": stats["cubic_segments"],
        "segments": stats["line_segments"] + stats["cubic_segments"],
        "corners": stats["corners"],
        "svg_bytes": svg.stat().st_size,
        "params": params.as_metadata(),
        "preview": str(preview),
        "diff": str(diff),
        "svg": str(svg),
    }


def comparison_sheet(output_dir, round_name, items):
    images = [read_image(item["preview"], cv2.IMREAD_COLOR) for item in items]
    height = max(image.shape[0] for image in images)
    columns = []
    for item, image in zip(items, images):
        if image.shape[0] < height:
            image = cv2.copyMakeBorder(
                image,
                0,
                height - image.shape[0],
                0,
                0,
                cv2.BORDER_CONSTANT,
                value=(25, 25, 25),
            )
        image = cv2.copyMakeBorder(
            image, 46, 0, 0, 24, cv2.BORDER_CONSTANT, value=(25, 25, 25)
        )
        label = f"{item['name']}  diff {item['disagreement_pct']}%  seg {item['segments']}"
        cv2.putText(
            image,
            label,
            (12, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        columns.append(image)
    path = Path(output_dir) / f"compare_{round_name}.png"
    write_image(path, np.hstack(columns))
    return path


def run_sweep(mask_path, spec_path, output_dir, round_name="round", preview_width=900):
    spec_path = Path(spec_path)
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise LogoExtractError(f"Could not read sweep specification {spec_path}: {error}") from error
    if not isinstance(spec, dict) or not spec:
        raise LogoExtractError("Sweep specification must be a non-empty JSON object")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    results = [
        evaluate(mask_path, output_dir, name, params, preview_width)
        for name, params in spec.items()
    ]
    sheet = comparison_sheet(output_dir, round_name, results) if len(results) >= 2 else None
    report = {
        "mask": str(mask_path),
        "candidates": results,
        "comparison_sheet": str(sheet) if sheet else None,
    }
    write_text(output_dir / "results.json", json.dumps(report, indent=2) + "\n")
    return report
