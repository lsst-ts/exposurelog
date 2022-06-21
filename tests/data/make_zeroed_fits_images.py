#!/usr/bin/env python
import argparse
import pathlib

from astropy.io import fits


def make_zeroed_fits_images(
    srcdir: pathlib.Path | str,
    destdir: pathlib.Path | str,
    overwrite: bool = False,
) -> None:
    """Copy FITS images from srcdir to destdir, zeroing the image data
    and compress the results.

    Parameters
    ----------
    srcdir
        Path to the source directory.
        Process all files with ".fits" extension.
    destdir
        Path to the destination directory, which need not exist.
        Existing files will not be overwritten.
        The result is compressed with fpack but still has extension ".fits".
    overwrite
        Overwrite existing destination images?
    """
    srcdir = pathlib.Path(srcdir).resolve()
    destdir = pathlib.Path(destdir).resolve()
    if srcdir == destdir:
        raise RuntimeError("source cannot match destination")

    if not destdir.exists():
        print(f"Creating destination directory {destdir}/")
        destdir.mkdir()

    for srcimagepath in srcdir.glob("*.fits"):
        destimagepath = destdir / srcimagepath.name
        print(f"Proccessing {srcimagepath} -> {destimagepath.parent}")
        data = fits.open(srcimagepath)
        for i, hdu in enumerate(data):
            assert hdu.data is not None  # make linters happy
            if isinstance(hdu, fits.CompImageHDU):
                hdu.data[:] = 0
            elif isinstance(hdu, fits.ImageHDU):
                data[i] = fits.CompImageHDU(
                    data=hdu.data[:] * 0, header=hdu.header
                )
        data.writeto(destimagepath, overwrite=overwrite)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        "Make zeroed, highly compressed, FITS images"
    )
    parser.add_argument(
        "srcdir",
        help="Source directory; process all .fits files in this directory",
    )
    parser.add_argument(
        "destdir", help="Destination directory; created if it does not exist"
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="Overwrite existing images?"
    )
    args = parser.parse_args()
    make_zeroed_fits_images(
        srcdir=args.srcdir, destdir=args.destdir, overwrite=args.overwrite
    )
