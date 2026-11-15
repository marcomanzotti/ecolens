"""Blue Marble Earth image from NASA GIBS (WMS), checked and converted to WebP.

Uses the `cwebp` / `dwebp` command-line tools (libwebp) when present; no Python image library.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlencode

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray

GIBS_WMS = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
LAYER = "BlueMarble_ShadedRelief_Bathymetry"
JPEG_MAGIC = b"\xff\xd8\xff"
# A real Earth frame has many colours; a blank or error frame has (almost) one.
MIN_PIXEL_STD = 8.0
MAX_DOMINANT_SHARE = 0.9
WEBP_QUALITY = 82
PPM_MAGIC = b"P6"
PPM_HEADER_FIELDS = 4


class BlankFrameError(ValueError):
    """The image is not a usable Earth frame (error page, blank or single-colour image)."""


def wms_url(width: int) -> str:
    query = {
        "SERVICE": "WMS",
        "REQUEST": "GetMap",
        "VERSION": "1.3.0",
        "CRS": "EPSG:4326",
        "BBOX": "-90,-180,90,180",
        "STYLES": "",
        "LAYERS": LAYER,
        "FORMAT": "image/jpeg",
        "WIDTH": str(width),
        "HEIGHT": str(width // 2),
    }
    return f"{GIBS_WMS}?{urlencode(query)}"


def check_jpeg(data: bytes) -> None:
    """GIBS answers errors with an XML document and status 200: refuse anything but a JPEG."""
    if not data.startswith(JPEG_MAGIC):
        raise BlankFrameError("the response is not a JPEG image (probably a WMS error document)")


def check_not_blank(pixels: NDArray[np.uint8]) -> None:
    """Refuses an empty, constant or nearly single-colour frame. `pixels` is (h, w, 3)."""
    import numpy as np

    if pixels.size == 0:
        raise BlankFrameError("the image has no pixels")
    if float(pixels.std()) < MIN_PIXEL_STD:
        raise BlankFrameError("the image is blank (almost no variation between pixels)")
    flat = pixels.reshape(-1, pixels.shape[-1])
    _, counts = np.unique(flat, axis=0, return_counts=True)
    if counts.max() / flat.shape[0] > MAX_DOMINANT_SHARE:
        raise BlankFrameError("the image is a single colour over most of its area")


def parse_ppm(data: bytes) -> NDArray[np.uint8]:
    """Binary PPM (P6, maxval 255) as written by `dwebp -ppm`."""
    import numpy as np

    fields: list[bytes] = []
    position = 0
    while len(fields) < PPM_HEADER_FIELDS:
        while data[position : position + 1].isspace():
            position += 1
        end = position
        while not data[end : end + 1].isspace():
            end += 1
        fields.append(data[position:end])
        position = end
    position += 1  # the single whitespace after maxval
    if fields[0] != PPM_MAGIC or int(fields[3]) != 255:
        raise ValueError("unsupported PPM image")
    width, height = int(fields[1]), int(fields[2])
    return np.frombuffer(data, dtype=np.uint8, count=width * height * 3, offset=position).reshape(
        height, width, 3
    )


def _tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"`{name}` (libwebp) is needed to write WebP: brew install webp")
    return path


def jpeg_to_webp(source: Path, target: Path, scratch: Path) -> None:
    """Converts, then decodes the WebP again and refuses it if it is blank."""
    subprocess.run(
        [
            _tool("cwebp"),
            "-quiet",
            "-q",
            str(WEBP_QUALITY),
            "-m",
            "6",
            str(source),
            "-o",
            str(target),
        ],
        check=True,
    )
    ppm = scratch / f"{target.stem}.ppm"
    subprocess.run([_tool("dwebp"), "-quiet", str(target), "-ppm", "-o", str(ppm)], check=True)
    try:
        check_not_blank(parse_ppm(ppm.read_bytes()))
    finally:
        ppm.unlink(missing_ok=True)
