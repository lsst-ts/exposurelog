__all__ = ["current_date_and_day_obs"]

import astropy.time

HalfDayDelta = astropy.time.TimeDelta(0.5, format="jd")


def current_date_and_day_obs() -> tuple[astropy.time.Time, int]:
    """Return the current date and day_obs.

    This uses Rubin Observatory's standard definition::

      day_obs = TAI time - 12 hours
    """
    current_date = astropy.time.Time.now()
    day_obs_full = current_date.tai - HalfDayDelta
    return current_date, int(day_obs_full.strftime("%Y%m%d"))
