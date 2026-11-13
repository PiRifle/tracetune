---
name: tracetune
description: Use the TraceTune CLI or Python API to convert raster logos and icons into optimized SVG paths. Use for raster-to-SVG conversion, mask preparation, quality presets, a 0-100 optimization control, SVG element inspection, Bézier fitting, parameter sweeps, pixel diffs, and wireframes.
---

# TraceTune

Use this skill to operate the project in the current repository. Read `../../../README.md` when detailed command options or installation instructions are needed.

## Choose the approach

- Use `tracetune` for high-contrast silhouettes, logos, and icons with meaningful raster detail.
- Split multicolor artwork into registered monochrome layers and fit each layer separately. The fitter writes black paths; set the intended fill when combining layers.
- For very simple geometric icons, hand-drawn SVG may be cleaner than tracing. Use the `svg-icon-optimization` skill for that workflow.
- Do not describe the tool as a full-color automatic vectorizer.

## Prepare the environment

Prefer an existing project virtual environment. Otherwise create one inside the repository:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/tracetune --help
```

Use `tracetune` directly when it is already installed. For `optimize`, `diff`, and `sweep`, confirm that `rsvg-convert` is available. Do not install system packages or change the user's global Python environment without permission.

## Start with the easy controls

Use one command for the common case:

```sh
tracetune optimize MASK outputs/logo.svg
tracetune inspect outputs/logo.svg
```

`optimize` defaults to the balanced preset and writes the SVG, metadata, rendered PNG, and pixel diff. Its `--quality` option is the terminal equivalent of one slider: 0 is compact, 65 is balanced, 100 is detailed, and intermediate values interpolate between presets. Use `--preset compact|balanced|detailed` when a named setting is clearer. Run `tracetune presets` to look up the exact parameter values.

Prefer these controls for users who do not specify geometric tolerances. Move to `fit` or `sweep` when explicit per-parameter control is needed.

## Run the standard workflow

Inspect the source image first. Preserve the original and write generated files to the requested destination or `outputs/`.

```sh
tracetune prepare INPUT outputs/mask.png
tracetune optimize outputs/mask.png outputs/logo.svg
tracetune inspect outputs/logo.svg
tracetune wireframe outputs/logo.svg outputs/wireframe.png
```

The mask must contain white foreground on black. Use `prepare --invert` for dark artwork on a light background. If thresholding leaves gaps or merges details, adjust `--threshold` before fitting. All fitting tolerances are measured in prepared-mask pixels.

For a small source, increasing `prepare --scale` gives the fitter more geometric resolution. Do not upscale repeatedly or overwrite the source.

## Tune with evidence

Start with balanced optimization, then adjust `--quality` based on the render and diff. Increase quality to preserve detail; decrease it to reduce path count. For advanced tuning, increase `fit --tol` and `--sigma` to simplify the result or reduce them to preserve detail. Use `--min-area` cautiously because it can remove intentional small shapes.

For several plausible settings, create a JSON specification and run:

```sh
tracetune sweep MASK spec.json outputs/candidates --round-name tuning
tracetune zoom outputs/candidates outputs/detail.png X Y WIDTH HEIGHT NAME1 NAME2
```

Read `results.json`, the comparison sheet, diff images, and zoomed details. Select based on both visual fidelity and segment count, not file size alone. Every sweep candidate starts from defaults, so unspecified parameters do not inherit another candidate's values.

Diff colors are green for matching foreground, red for missing SVG coverage, and blue for extra SVG coverage. The percentage is relative to mask foreground area.

## Preserve multicolor registration

When fitting color layers separately:

1. Create every mask from the same uncropped canvas, or record and reapply exactly the same crop and scale.
2. Fit each mask without independently recentering its output.
3. Combine paths under one SVG with the original shared `viewBox`.
4. Assign each path its intended color and use `fill-rule="evenodd"` for holes.
5. Render the combined SVG and inspect edges where colors meet.

## Verify before delivery

- Run `tracetune inspect FINAL.svg` and review drawing elements, colors, subpaths, command counts, and embedded-raster status.
- Parse the SVG as XML and confirm a valid, positive `viewBox`.
- Render the actual final SVG, not an intermediate candidate, and view the PNG.
- Inspect both the intended display size and an enlarged render for gaps, touching strokes, distorted corners, and lost holes.
- Confirm there is no embedded raster image unless the user explicitly requested one.
- Keep the final SVG, source mask when applicable, and useful comparison images.
- Report output paths, tuning parameters, path/segment counts, and any remaining visual differences.

Use the Python API for scripted batch work:

```python
from tracetune import FitParameters, vectorize_mask

params = FitParameters(tol=4.0, line_tol=1.8, smooth_sigma=7.0)
stats = vectorize_mask("outputs/mask.png", "outputs/logo.svg", params=params)
```
