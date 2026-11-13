import argparse
import json
import sys
from pathlib import Path

from . import __version__
from ._io import LogoExtractError
from .compare import compare_svg
from .fit import vectorize_mask
from .inspect_svg import inspect_svg
from .mask import prepare_mask
from .optimize import list_presets, optimize_mask
from .sweep import run_sweep
from .wireframe import wireframe_svg
from .zoom import zoom_candidates


def print_result(result):
    print(json.dumps(result, indent=2))


def prepare_command(args):
    print_result(
        prepare_mask(
            args.input,
            args.output,
            threshold=args.threshold,
            padding=args.padding,
            scale=args.scale,
            blur_sigma=args.blur_sigma,
            invert=args.invert,
        )
    )


def fit_command(args):
    params = {}
    for argument, key in (
        (args.tol, "tol"),
        (args.line_tol, "line_tol"),
        (args.sigma, "smooth_sigma"),
        (args.min_area, "min_area"),
    ):
        if argument is not None:
            params[key] = argument
    stats = vectorize_mask(args.mask, args.output, args.meta, params)
    metadata = args.meta or str(Path(args.output).with_suffix(".meta.json"))
    print_result({"output": args.output, "metadata": metadata, "stats": stats})


def optimize_command(args):
    print_result(
        optimize_mask(
            args.mask,
            args.output,
            quality=args.quality,
            preset=args.preset,
            min_area=args.min_area,
            render_path=args.render,
            diff_path=args.diff,
        )
    )


def presets_command(args):
    print_result(list_presets())


def inspect_command(args):
    print_result(inspect_svg(args.svg))


def diff_command(args):
    print_result(compare_svg(args.mask, args.svg, args.output, args.render))


def wireframe_command(args):
    print_result(wireframe_svg(args.svg, args.output, args.meta))


def sweep_command(args):
    report = run_sweep(
        args.mask,
        args.spec,
        args.output_dir,
        round_name=args.round_name,
        preview_width=args.preview_width,
    )
    for candidate in report["candidates"]:
        print_result(candidate)
    print_result(
        {"results": f"{args.output_dir}/results.json", "comparison_sheet": report["comparison_sheet"]}
    )


def zoom_command(args):
    print_result(
        zoom_candidates(
            args.candidate_dir,
            args.output,
            args.x,
            args.y,
            args.width,
            args.height,
            args.names,
            scale=args.scale,
        )
    )


def build_parser():
    parser = argparse.ArgumentParser(
        prog="tracetune",
        description="Turn high-contrast raster logos into compact SVG paths and inspect the fit.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="threshold, crop, and smooth a raster image")
    prepare.add_argument("input", help="source raster image")
    prepare.add_argument("output", help="output mask PNG")
    prepare.add_argument("--threshold", type=int, default=140, help="grayscale threshold (default: 140)")
    prepare.add_argument("--padding", type=int, default=6, help="crop padding in source pixels (default: 6)")
    prepare.add_argument("--scale", type=float, default=3, help="upscale factor before smoothing (default: 3)")
    prepare.add_argument("--blur-sigma", type=float, default=4, help="Gaussian blur sigma (default: 4)")
    prepare.add_argument("--invert", action="store_true", help="extract a dark logo on a light background")
    prepare.set_defaults(handler=prepare_command)

    optimize = subparsers.add_parser(
        "optimize", help="fit, render, and evaluate an SVG with simple quality controls"
    )
    optimize.add_argument("mask", help="binary mask PNG")
    optimize.add_argument("output", help="output SVG; render and diff paths are derived from it")
    quality_group = optimize.add_mutually_exclusive_group()
    quality_group.add_argument(
        "--quality",
        type=float,
        help="detail level from 0 (compact) through 65 (balanced) to 100 (detailed)",
    )
    quality_group.add_argument(
        "--preset", choices=("compact", "balanced", "detailed"), help="named optimization preset"
    )
    optimize.add_argument("--min-area", type=float, help="minimum contour area in pixels (default: 600)")
    optimize.add_argument("--render", help="rendered PNG path (default: OUTPUT with .png suffix)")
    optimize.add_argument("--diff", help="difference PNG path (default: OUTPUT with .diff.png suffix)")
    optimize.set_defaults(handler=optimize_command)

    presets = subparsers.add_parser("presets", help="show the optimization preset lookup table")
    presets.set_defaults(handler=presets_command)

    inspect = subparsers.add_parser("inspect", help="summarize SVG elements, colors, and path commands")
    inspect.add_argument("svg", help="SVG file to inspect")
    inspect.set_defaults(handler=inspect_command)

    fit = subparsers.add_parser("fit", help="fit straight lines and cubic Béziers to a mask")
    fit.add_argument("mask", help="binary mask PNG")
    fit.add_argument("output", help="output SVG")
    fit.add_argument("--meta", help="metadata JSON path (default: OUTPUT with .meta.json suffix)")
    fit.add_argument("--tol", type=float, help="maximum cubic deviation in mask pixels (default: 1.5)")
    fit.add_argument("--line-tol", type=float, help="maximum straight-line deviation (default: 1.2)")
    fit.add_argument("--sigma", type=float, help="contour smoothing sigma (default: 4)")
    fit.add_argument("--min-area", type=float, help="minimum contour area in pixels (default: 600)")
    fit.set_defaults(handler=fit_command)

    diff = subparsers.add_parser("diff", help="render an SVG and compare it with its mask")
    diff.add_argument("mask", help="reference binary mask PNG")
    diff.add_argument("svg", help="SVG to render")
    diff.add_argument("output", help="output difference PNG")
    diff.add_argument("--render", help="also keep the rendered SVG at this PNG path")
    diff.set_defaults(handler=diff_command)

    wireframe = subparsers.add_parser("wireframe", help="draw anchors and Bézier control handles")
    wireframe.add_argument("svg", help="SVG produced by the fit command")
    wireframe.add_argument("output", help="output wireframe PNG")
    wireframe.add_argument("--meta", help="metadata JSON (default: SVG with .meta.json suffix)")
    wireframe.set_defaults(handler=wireframe_command)

    sweep = subparsers.add_parser("sweep", help="compare several fit parameter sets")
    sweep.add_argument("mask", help="reference binary mask PNG")
    sweep.add_argument("spec", help="JSON object mapping candidate names to parameters")
    sweep.add_argument("output_dir", help="directory for SVGs, renders, diffs, and results.json")
    sweep.add_argument("--round-name", default="round", help="comparison sheet suffix (default: round)")
    sweep.add_argument("--preview-width", type=int, default=900, help="candidate preview width (default: 900)")
    sweep.set_defaults(handler=sweep_command)

    zoom = subparsers.add_parser("zoom", help="compare the same crop across sweep candidates")
    zoom.add_argument("candidate_dir", help="sweep output directory")
    zoom.add_argument("output", help="output comparison PNG")
    zoom.add_argument("x", type=int)
    zoom.add_argument("y", type=int)
    zoom.add_argument("width", type=int)
    zoom.add_argument("height", type=int)
    zoom.add_argument("names", nargs="+", help="candidate names from the sweep specification")
    zoom.add_argument("--scale", type=int, default=2, help="integer crop magnification (default: 2)")
    zoom.set_defaults(handler=zoom_command)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.handler(args)
    except (LogoExtractError, FileNotFoundError, ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0
