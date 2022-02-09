#!/usr/bin/env python
import lsst.daf.butler


def print_registry_contents(name: str) -> None:
    """Print the contents of a registry.

    Parameters
    ----------
    name
        The instrument name, which must match the registry name, e.g. "LATISS".
    """
    print(f"\nregistry=instrument={name}\n")
    butler = lsst.daf.butler.Butler(name, writeable=False)
    registry = butler.registry
    record_iter = registry.queryDimensionRecords(
        "exposure",
        instrument=name,
    )
    for record in record_iter:
        print(f"id={record.id}")
        print(record)


if __name__ == "__main__":
    for name in ("LSSTCam", "LATISS"):
        print_registry_contents(name)
