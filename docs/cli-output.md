# Complete CLI output reference

These are real captured stdout results from TraceTune 0.2.0 using the bundled Papirus audio-volume icon. Paths and values are from the capture; results for other images will differ.

## Version

```sh
tracetune --version
```

```text
tracetune 0.2.0
```

No files; prints the installed version.

## Prepare a mask

```sh
tracetune prepare source.png outputs/cli-docs/mask.png --invert --scale 3
```

```json
{
  "width": 1125,
  "height": 1056,
  "output": "outputs/cli-docs/mask.png"
}
```

Creates `mask.png` with white foreground on black.

## Optimize with balanced quality

```sh
tracetune optimize examples/mask.png outputs/cli-docs/optimized.svg --quality 65
```

```json
{
  "quality": 65.0,
  "preset": null,
  "output": "outputs/cli-docs/optimized.svg",
  "metadata": "outputs/cli-docs/optimized.meta.json",
  "render": "outputs/cli-docs/optimized.png",
  "diff": "outputs/cli-docs/optimized.diff.png",
  "parameters": {
    "tol": 4.0,
    "line_tol": 1.8,
    "smooth_sigma": 7.0,
    "min_area": 600.0
  },
  "stats": {
    "contours": 3,
    "corners": 12,
    "line_segments": 19,
    "cubic_segments": 8,
    "viewbox": [
      1125,
      1056
    ]
  },
  "comparison": {
    "disagreement_pct": 1.1726,
    "disagreement_px": 6194,
    "missing_px": 4654,
    "extra_px": 1540,
    "output": "outputs/cli-docs/optimized.diff.png"
  }
}
```

Creates the SVG, `.meta.json`, rendered `.png`, and `.diff.png`.

## List optimization presets

```sh
tracetune presets
```

```json
[
  {
    "name": "compact",
    "quality": 0,
    "description": "Fewer segments and a smaller SVG",
    "tol": 11.0,
    "line_tol": 2.5,
    "smooth_sigma": 10.0
  },
  {
    "name": "balanced",
    "quality": 65,
    "description": "A practical balance of fidelity and size",
    "tol": 4.0,
    "line_tol": 1.8,
    "smooth_sigma": 7.0
  },
  {
    "name": "detailed",
    "quality": 100,
    "description": "Maximum detail with more segments",
    "tol": 1.5,
    "line_tol": 1.2,
    "smooth_sigma": 4.0
  }
]
```

No files; prints the preset lookup table.

## Inspect SVG elements

```sh
tracetune inspect examples/optimized.svg
```

```json
{
  "file": "examples/optimized.svg",
  "bytes": 791,
  "title": null,
  "viewBox": "0 0 1125 1056",
  "width": "1125",
  "height": "1056",
  "summary": {
    "drawing_elements": 1,
    "paths": 1,
    "path_commands": {
      "C": 8,
      "L": 19,
      "M": 3,
      "Z": 3
    },
    "colors": [
      "#000000"
    ],
    "embedded_raster": false
  },
  "elements": [
    {
      "index": 1,
      "tag": "path",
      "fill": "#000000",
      "fill-rule": "evenodd",
      "commands": {
        "C": 8,
        "L": 19,
        "M": 3,
        "Z": 3
      },
      "subpaths": 3
    }
  ]
}
```

No files; prints element, color, path-command, and raster-payload details.

## Fit with advanced parameters

```sh
tracetune fit examples/mask.png outputs/cli-docs/fitted.svg --tol 1.5 --line-tol 1.2 --sigma 4
```

```json
{
  "output": "outputs/cli-docs/fitted.svg",
  "metadata": "outputs/cli-docs/fitted.meta.json",
  "stats": {
    "contours": 3,
    "corners": 12,
    "line_segments": 31,
    "cubic_segments": 23,
    "viewbox": [
      1125,
      1056
    ]
  }
}
```

Creates `fitted.svg` and `fitted.meta.json`.

## Render and compare

```sh
tracetune diff examples/mask.png examples/optimized.svg outputs/cli-docs/diff.png --render outputs/cli-docs/render.png
```

```json
{
  "disagreement_pct": 1.1726,
  "disagreement_px": 6194,
  "missing_px": 4654,
  "extra_px": 1540,
  "output": "outputs/cli-docs/diff.png"
}
```

Creates `diff.png` and `render.png`, and reports missing, extra, and total disagreement pixels.

## Draw the Bézier wireframe

```sh
tracetune wireframe examples/optimized.svg outputs/cli-docs/wireframe.png
```

```json
{
  "anchors": 30,
  "control_points": 16,
  "output": "outputs/cli-docs/wireframe.png"
}
```

Creates `wireframe.png` and reports anchor and control-point counts.

## Run a parameter sweep

```sh
tracetune sweep examples/mask.png examples/sweep.json outputs/cli-docs/sweep --round-name demo --preview-width 300
```

```json
{
  "name": "detailed",
  "disagreement_pct": 0.7395,
  "missing_px": 3412,
  "extra_px": 494,
  "lines": 31,
  "cubics": 23,
  "segments": 54,
  "corners": 12,
  "svg_bytes": 1600,
  "params": {
    "TOL": 1.5,
    "LINE_TOL": 1.2,
    "SMOOTH_SIGMA": 4.0,
    "corner_scales": [
      [
        8.0,
        45.0
      ],
      [
        16.0,
        55.0
      ],
      [
        32.0,
        75.0
      ]
    ],
    "corner_nms_radius": 12,
    "thinning_epsilon": 0.2,
    "min_contour_area": 600.0,
    "reparam_iterations": 4,
    "max_depth": 40,
    "min_run": 8,
    "run_sigma_factor": 6.0,
    "junction_snap": 80.0
  },
  "preview": "outputs/cli-docs/sweep/detailed_preview.png",
  "diff": "outputs/cli-docs/sweep/detailed_diff.png",
  "svg": "outputs/cli-docs/sweep/detailed.svg"
}
{
  "name": "balanced",
  "disagreement_pct": 1.1726,
  "missing_px": 4654,
  "extra_px": 1540,
  "lines": 19,
  "cubics": 8,
  "segments": 27,
  "corners": 12,
  "svg_bytes": 791,
  "params": {
    "TOL": 4.0,
    "LINE_TOL": 1.8,
    "SMOOTH_SIGMA": 7.0,
    "corner_scales": [
      [
        8.0,
        45.0
      ],
      [
        16.0,
        55.0
      ],
      [
        32.0,
        75.0
      ]
    ],
    "corner_nms_radius": 12,
    "thinning_epsilon": 0.2,
    "min_contour_area": 600.0,
    "reparam_iterations": 4,
    "max_depth": 40,
    "min_run": 8,
    "run_sigma_factor": 6.0,
    "junction_snap": 80.0
  },
  "preview": "outputs/cli-docs/sweep/balanced_preview.png",
  "diff": "outputs/cli-docs/sweep/balanced_diff.png",
  "svg": "outputs/cli-docs/sweep/balanced.svg"
}
{
  "name": "compact",
  "disagreement_pct": 3.6932,
  "missing_px": 11442,
  "extra_px": 8066,
  "lines": 17,
  "cubics": 4,
  "segments": 21,
  "corners": 12,
  "svg_bytes": 598,
  "params": {
    "TOL": 11.0,
    "LINE_TOL": 2.5,
    "SMOOTH_SIGMA": 10.0,
    "corner_scales": [
      [
        8.0,
        45.0
      ],
      [
        16.0,
        55.0
      ],
      [
        32.0,
        75.0
      ]
    ],
    "corner_nms_radius": 12,
    "thinning_epsilon": 0.2,
    "min_contour_area": 600.0,
    "reparam_iterations": 4,
    "max_depth": 40,
    "min_run": 8,
    "run_sigma_factor": 6.0,
    "junction_snap": 80.0
  },
  "preview": "outputs/cli-docs/sweep/compact_preview.png",
  "diff": "outputs/cli-docs/sweep/compact_diff.png",
  "svg": "outputs/cli-docs/sweep/compact.svg"
}
{
  "results": "outputs/cli-docs/sweep/results.json",
  "comparison_sheet": "outputs/cli-docs/sweep/compare_demo.png"
}
```

Creates each candidate SVG, metadata, full render, preview, and diff, plus `results.json` and `compare_demo.png`.

## Compare a zoomed crop

```sh
tracetune zoom outputs/cli-docs/sweep outputs/cli-docs/zoom.png 500 0 500 500 detailed compact --scale 2
```

```json
{
  "candidates": [
    "detailed",
    "compact"
  ],
  "width": 2032,
  "height": 1046,
  "output": "outputs/cli-docs/zoom.png"
}
```

Creates `zoom.png` from the matching full-resolution candidate renders.
