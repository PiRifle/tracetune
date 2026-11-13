from pathlib import Path

import cv2


class LogoExtractError(Exception):
    pass


def read_image(path, flags=cv2.IMREAD_GRAYSCALE):
    path = Path(path)
    if not path.is_file():
        raise LogoExtractError(f"Image not found: {path}")
    image = cv2.imread(str(path), flags)
    if image is None:
        raise LogoExtractError(f"Could not decode image: {path}")
    return image


def write_image(path, image):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), image):
        raise LogoExtractError(f"Could not write image: {path}")
    return path


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
