from pathlib import Path

import cv2
import numpy as np

from ._io import read_image, write_image
from .sweep import candidate_path


def zoom_candidates(candidate_dir, output_path, x, y, width, height, names, scale=2):
    if width <= 0 or height <= 0 or scale <= 0:
        raise ValueError("width, height, and scale must be greater than zero")
    if x < 0 or y < 0:
        raise ValueError("x and y must be non-negative")
    if not names:
        raise ValueError("At least one candidate name is required")

    columns = []
    for name in names:
        path = candidate_path(candidate_dir, name, "_full.png")
        image = read_image(path, cv2.IMREAD_COLOR)
        if x + width > image.shape[1] or y + height > image.shape[0]:
            raise ValueError(
                f"Crop ({x}, {y}, {width}, {height}) exceeds {name} image dimensions "
                f"{image.shape[1]}x{image.shape[0]}"
            )
        crop = image[y : y + height, x : x + width]
        crop = cv2.resize(
            crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST
        )
        crop = cv2.copyMakeBorder(
            crop, 46, 0, 0, 16, cv2.BORDER_CONSTANT, value=(25, 25, 25)
        )
        cv2.putText(
            crop,
            name,
            (12, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 255),
            2,
            cv2.LINE_AA,
        )
        columns.append(crop)

    write_image(output_path, np.hstack(columns))
    return {
        "candidates": list(names),
        "width": columns[0].shape[1] * len(columns),
        "height": columns[0].shape[0],
        "output": str(Path(output_path)),
    }
