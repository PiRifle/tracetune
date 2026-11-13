import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import cv2
import numpy as np

from ._io import LogoExtractError, write_image

NUMBER = r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"


def bezier(points, count=120):
    t = np.linspace(0, 1, count)[:, None]
    basis = np.hstack(
        [(1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t**3]
    )
    return basis @ points


def svg_dimensions(root):
    try:
        if "width" in root.attrib and "height" in root.attrib:
            width = float(root.attrib["width"].removesuffix("px"))
            height = float(root.attrib["height"].removesuffix("px"))
        else:
            _, _, width, height = (
                float(value) for value in root.attrib["viewBox"].split()
            )
    except (KeyError, ValueError) as error:
        raise LogoExtractError("SVG must have numeric width/height or a viewBox") from error
    if width <= 0 or height <= 0:
        raise LogoExtractError("SVG dimensions must be positive")
    return width, height


def wireframe_svg(svg_path, output_path, meta_path=None):
    svg_path = Path(svg_path)
    try:
        root = ET.parse(svg_path).getroot()
    except (OSError, ET.ParseError) as error:
        raise LogoExtractError(f"Could not read SVG {svg_path}: {error}") from error
    width, height = svg_dimensions(root)
    path_data = " ".join(
        element.attrib.get("d", "")
        for element in root.iter()
        if element.tag.rsplit("}", 1)[-1] == "path"
    )
    if not path_data:
        raise LogoExtractError(f"SVG has no path data: {svg_path}")

    canvas = np.zeros((int(round(height)), int(round(width)), 3), np.uint8)
    anchors, controls, handles = [], [], []
    current = None
    start = None
    commands = list(re.finditer(r"([A-Za-z])([^A-Za-z]*)", path_data))
    for match in commands:
        command, arguments = match.groups()
        numbers = [float(value) for value in re.findall(NUMBER, arguments)]
        if command == "M":
            if len(numbers) != 2:
                raise LogoExtractError("Only single-coordinate M commands are supported")
            current = np.array(numbers)
            start = current.copy()
            anchors.append(current)
        elif command == "L" and current is not None:
            if len(numbers) != 2:
                raise LogoExtractError("Only single-coordinate L commands are supported")
            point = np.array(numbers)
            line = np.stack([current, point])
            cv2.polylines(
                canvas, [line.astype(np.int32)], False, (255, 255, 255), 1, cv2.LINE_AA
            )
            anchors.append(point)
            current = point
        elif command == "C" and current is not None:
            if len(numbers) != 6:
                raise LogoExtractError("Only single-segment C commands are supported")
            control = np.array(numbers).reshape(3, 2)
            curve = bezier(np.vstack([current, control]))
            cv2.polylines(
                canvas, [curve.astype(np.int32)], False, (255, 255, 255), 1, cv2.LINE_AA
            )
            handles.extend([(current, control[0]), (control[2], control[1])])
            controls.extend([control[0], control[1]])
            anchors.append(control[2])
            current = control[2]
        elif command == "Z":
            if current is not None and start is not None and not np.array_equal(current, start):
                line = np.stack([current, start])
                cv2.polylines(
                    canvas, [line.astype(np.int32)], False, (255, 255, 255), 1, cv2.LINE_AA
                )
            current = start
        else:
            raise LogoExtractError(f"Unsupported SVG path command: {command}")

    for anchor, control in handles:
        cv2.line(
            canvas,
            tuple(anchor.astype(int)),
            tuple(control.astype(int)),
            (80, 80, 80),
            1,
            cv2.LINE_AA,
        )
    for point in controls:
        cv2.circle(canvas, tuple(point.astype(int)), 3, (255, 120, 0), 1, cv2.LINE_AA)
    for point in anchors:
        cv2.rectangle(
            canvas,
            tuple((point - 3).astype(int)),
            tuple((point + 3).astype(int)),
            (0, 220, 0),
            1,
            cv2.LINE_AA,
        )

    lines = [f"{svg_path.name} - fit parameters"]
    metadata_path = Path(meta_path) if meta_path else svg_path.with_suffix(".meta.json")
    if metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        for key, value in metadata.get("parameters", {}).items():
            lines.append(f"  {key}: {value}")
        lines.append("stats")
        for key, value in metadata.get("stats", {}).items():
            lines.append(f"  {key}: {value}")
    elif meta_path:
        raise LogoExtractError(f"Metadata not found: {metadata_path}")
    else:
        lines.append("  no metadata file found")

    font, scale, thickness = cv2.FONT_HERSHEY_SIMPLEX, 1.0, 2
    sizes = [cv2.getTextSize(text, font, scale, thickness)[0] for text in lines]
    box_width = max(size[0] for size in sizes) + 40
    box_height = sum(size[1] + 12 for size in sizes) + 28
    overlay = canvas.copy()
    cv2.rectangle(overlay, (20, 20), (20 + box_width, 20 + box_height), (30, 30, 30), -1)
    cv2.addWeighted(overlay, 0.8, canvas, 0.2, 0, canvas)
    cv2.rectangle(canvas, (20, 20), (20 + box_width, 20 + box_height), (90, 90, 90), 1)
    y = 52
    for text, (_, text_height) in zip(lines, sizes):
        cv2.putText(canvas, text, (40, y), font, scale, (220, 220, 220), thickness, cv2.LINE_AA)
        y += text_height + 12

    write_image(output_path, canvas)
    return {
        "anchors": len(anchors),
        "control_points": len(controls),
        "output": str(Path(output_path)),
    }
