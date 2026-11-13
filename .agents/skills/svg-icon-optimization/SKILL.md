---
name: svg-icon-optimization
description: Create, recreate, simplify, and visually review clean SVG icons and logos. Use for hand-drawing vector icons from a reference, optimizing SVG paths, correcting proportions or stroke spacing, removing raster payloads, and validating scalable icon deliverables.
---

# SVG Icon Optimization

Use this skill for small geometric artwork where deliberate SVG construction can outperform automatic tracing. Use `tracetune` instead when the source has substantial raster detail or the user specifically requests contour fitting.

## Reconstruct the design

1. View the reference and identify its separate visual components, colors, negative spaces, stroke widths, and approximate bounding boxes.
2. Choose a tight, integer `viewBox` with consistent margins. Preserve the reference aspect ratio and alignment between components.
3. Build the icon from simple paths and shapes. Prefer shared paths for repeated strokes, cubic curves for smooth outlines, and `fill-rule="evenodd"` for cutouts.
4. Use rounded `stroke-linecap` and `stroke-linejoin` when the reference has soft terminals and corners.
5. Leave the background and internal cutouts transparent unless a filled background is part of the design.

For reference colors, sample the source image when pixel access is available. Otherwise choose a close color and disclose that the result is a visual recreation rather than a pixel-exact trace.

## Optimize without damaging the icon

- Combine compatible subpaths that share fill and stroke attributes.
- Use integers or the minimum practical decimal precision.
- Remove redundant commands, unused definitions, metadata, transforms, and invisible elements.
- Avoid unnecessary groups, masks, clip paths, filters, embedded fonts, CSS, and base64 images.
- Preserve the `viewBox`; do not replace it with fixed dimensions alone.
- Preserve accessible labeling with `<title>` and appropriate `role`/`aria-labelledby` attributes. Keep IDs unique when inline icons are combined.
- Keep paths readable enough to edit. Do not sacrifice geometry or accessibility merely to save a few bytes.

If `scour` is already installed, it can provide an additional optimization pass. Check availability before using it, keep an unminified source when useful, and render the optimized result afterward. Do not add a new dependency solely for minification.

## Review visually

Render with `rsvg-convert` when available:

```sh
mkdir -p outputs/icon-review
rsvg-convert -b white -w 768 -o outputs/icon-review/icon.png icon.svg
```

View the generated PNG with the agent's image tool. Also render near the intended display size when small-size clarity matters. Check:

- silhouette and component proportions against the reference;
- consistent stroke weight and rounded terminals;
- clear gaps between adjacent strokes and outlines;
- smooth curves without accidental kinks;
- centered, intentional margins and a correct aspect ratio;
- clean holes and transparent regions on both light and dark backgrounds when relevant.

Refine the path and render again after every visual correction. Do not deliver from XML inspection alone.

## Validate the final file

Run `tracetune inspect icon.svg` for an element lookup covering paths, subpaths, colors, strokes, command counts, file size, and embedded-raster status. Use this to catch accidental extra elements and duplicated geometry.

Use `xmllint --noout icon.svg` when installed, or Python's standard library:

```sh
python3 -c 'import xml.etree.ElementTree as ET; ET.parse("icon.svg")'
```

Confirm the final file contains no `<image>` element or raster data URI. Report the output path, byte size, number of drawing elements, and verification performed. If the reference was only a visual preview or the result is approximate, say so plainly.

The repository's `examples/papirus/` directory contains unmodified Papirus system icons for repeatable inspections and fitting tests. Preserve the included GPL-3.0 license and upstream attribution when redistributing those assets or derived demonstrations.
