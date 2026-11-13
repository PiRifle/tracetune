import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from ._io import LogoExtractError

DRAWING_ELEMENTS = {
    "path",
    "rect",
    "circle",
    "ellipse",
    "line",
    "polyline",
    "polygon",
    "text",
    "image",
    "use",
}


def local_name(tag):
    return tag.rsplit("}", 1)[-1]


def inspect_svg(svg_path):
    svg_path = Path(svg_path)
    try:
        root = ET.parse(svg_path).getroot()
    except (OSError, ET.ParseError) as error:
        raise LogoExtractError(f"Could not read SVG {svg_path}: {error}") from error
    if local_name(root.tag) != "svg":
        raise LogoExtractError(f"Document root is not an SVG element: {svg_path}")

    elements = []
    command_totals = Counter()
    colors = set()
    embedded_raster = False
    for element in root.iter():
        tag = local_name(element.tag)
        if tag == "image" or "data:image" in ET.tostring(element, encoding="unicode"):
            embedded_raster = True
        if tag not in DRAWING_ELEMENTS:
            continue
        item = {"index": len(elements) + 1, "tag": tag}
        inline_style = {}
        for declaration in element.attrib.get("style", "").split(";"):
            if ":" in declaration:
                key, value = declaration.split(":", 1)
                inline_style[key.strip()] = value.strip()
        for attribute in ("id", "fill", "stroke", "stroke-width", "fill-rule"):
            value = element.attrib.get(attribute, inline_style.get(attribute))
            if value is not None:
                item[attribute] = value
        for color_attribute in ("fill", "stroke"):
            color = element.attrib.get(color_attribute, inline_style.get(color_attribute))
            if color and color != "none":
                colors.add(color)
        if tag == "path":
            commands = Counter(
                re.findall(r"[AaCcHhLlMmQqSsTtVvZz]", element.attrib.get("d", ""))
            )
            command_totals.update(commands)
            item["commands"] = dict(sorted(commands.items()))
            item["subpaths"] = commands["M"] + commands["m"]
        elements.append(item)

    title = next(
        (element.text for element in root.iter() if local_name(element.tag) == "title"),
        None,
    )
    return {
        "file": str(svg_path),
        "bytes": svg_path.stat().st_size,
        "title": title,
        "viewBox": root.attrib.get("viewBox"),
        "width": root.attrib.get("width"),
        "height": root.attrib.get("height"),
        "summary": {
            "drawing_elements": len(elements),
            "paths": sum(item["tag"] == "path" for item in elements),
            "path_commands": dict(sorted(command_totals.items())),
            "colors": sorted(colors),
            "embedded_raster": embedded_raster,
        },
        "elements": elements,
    }
