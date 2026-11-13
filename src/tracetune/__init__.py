from .compare import compare_svg
from .fit import FitParameters, vectorize_mask
from .inspect_svg import inspect_svg
from .mask import prepare_mask
from .optimize import optimize_mask

__version__ = "0.2.0"

__all__ = [
    "FitParameters",
    "compare_svg",
    "inspect_svg",
    "optimize_mask",
    "prepare_mask",
    "vectorize_mask",
    "__version__",
]
