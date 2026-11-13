from pathlib import Path

import cv2

from ._io import LogoExtractError, read_image, write_image


def prepare_mask(
    source,
    output,
    *,
    threshold=140,
    padding=6,
    scale=3,
    blur_sigma=4.0,
    invert=False,
):
    if not 0 <= threshold <= 255:
        raise ValueError("threshold must be between 0 and 255")
    if padding < 0:
        raise ValueError("padding must be non-negative")
    if scale <= 0:
        raise ValueError("scale must be greater than zero")
    if blur_sigma < 0:
        raise ValueError("blur_sigma must be non-negative")

    image = read_image(source)
    mode = cv2.THRESH_BINARY_INV if invert else cv2.THRESH_BINARY
    _, mask = cv2.threshold(image, threshold, 255, mode)
    foreground = cv2.findNonZero(mask)
    if foreground is None:
        raise LogoExtractError(
            "The mask is empty; adjust --threshold or use --invert for a dark logo on a light background"
        )

    ys = foreground[:, 0, 1]
    xs = foreground[:, 0, 0]
    y0 = max(int(ys.min()) - padding, 0)
    y1 = min(int(ys.max()) + padding + 1, mask.shape[0])
    x0 = max(int(xs.min()) - padding, 0)
    x1 = min(int(xs.max()) + padding + 1, mask.shape[1])
    mask = mask[y0:y1, x0:x1]

    enlarged = cv2.resize(mask, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    if blur_sigma:
        enlarged = cv2.GaussianBlur(
            enlarged, (0, 0), sigmaX=blur_sigma, sigmaY=blur_sigma
        )
    _, smooth = cv2.threshold(enlarged, 127, 255, cv2.THRESH_BINARY)
    write_image(output, smooth)
    return {"width": smooth.shape[1], "height": smooth.shape[0], "output": str(Path(output))}
