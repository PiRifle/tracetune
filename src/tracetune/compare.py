import shutil
import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

from ._io import LogoExtractError, read_image, write_image


def render_svg(svg_path, output_path):
    executable = shutil.which("rsvg-convert")
    if executable is None:
        raise LogoExtractError(
            "rsvg-convert is required for raster comparisons; install librsvg2-bin on Debian/Ubuntu or librsvg on Fedora"
        )
    svg_path = Path(svg_path)
    if not svg_path.is_file():
        raise LogoExtractError(f"SVG not found: {svg_path}")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [executable, "-b", "white", "-o", str(output_path), str(svg_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode:
        message = result.stderr.strip() or "unknown renderer error"
        raise LogoExtractError(f"Could not render {svg_path}: {message}")
    return output_path


def compare_arrays(mask, rendered, output_path):
    if rendered.shape != mask.shape:
        rendered = cv2.resize(
            rendered,
            (mask.shape[1], mask.shape[0]),
            interpolation=cv2.INTER_AREA,
        )
    mask_binary = mask > 127
    render_binary = rendered < 128
    foreground = int(mask_binary.sum())
    if foreground == 0:
        raise LogoExtractError("The mask has no foreground pixels")

    missing = int((mask_binary & ~render_binary).sum())
    extra = int((~mask_binary & render_binary).sum())
    disagreement = missing + extra
    visual = np.zeros((*mask_binary.shape, 3), np.uint8)
    visual[..., 1] = (mask_binary & render_binary) * 255
    visual[..., 2] = (mask_binary & ~render_binary) * 255
    visual[..., 0] = (~mask_binary & render_binary) * 255
    write_image(output_path, visual)
    return {
        "disagreement_pct": round(100.0 * disagreement / foreground, 4),
        "disagreement_px": disagreement,
        "missing_px": missing,
        "extra_px": extra,
        "output": str(Path(output_path)),
    }


def compare_svg(mask_path, svg_path, output_path, render_path=None):
    mask = read_image(mask_path)
    if render_path is not None:
        render_svg(svg_path, render_path)
        rendered = read_image(render_path)
        return compare_arrays(mask, rendered, output_path)
    with tempfile.TemporaryDirectory(prefix="tracetune-") as directory:
        temporary_render = Path(directory) / "render.png"
        render_svg(svg_path, temporary_render)
        rendered = read_image(temporary_render)
        return compare_arrays(mask, rendered, output_path)
