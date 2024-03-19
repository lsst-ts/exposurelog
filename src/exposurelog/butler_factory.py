from __future__ import annotations

from collections.abc import Iterator

import lsst.daf.butler

__all__ = ("ButlerFactory",)


class ButlerFactory:
    """Factory class for creating Butler instances.

    Instances are created quickly enough that a new one can be made for each
    incoming request.  However, creating an instance involves some non-trivial
    synchronous work, it is better not to call these functions directly from
    within an async function.

    Parameters
    ----------
    repositories
        A mapping from integer "registry" label to Butler configuration URI.
    """

    def __init__(self, repositories: dict[int, str]):
        self.repositories = tuple(repositories.keys())
        self.config_urls = tuple(repositories.values())
        self._factory = lsst.daf.butler.LabeledButlerFactory(
            {str(k): v for k, v in repositories.items()}
        )

    def is_valid_repository(self, repository: int) -> bool:
        """Return `True` if the specified repository was configured for the
        factory.
        """
        return repository in self.repositories

    def get_butler(self, repository: int) -> lsst.daf.butler.Butler:
        """Return a Butler instance for the specified repository."""
        return self._factory.create_butler(
            label=str(repository), access_token=None
        )

    def get_all_butlers(self) -> Iterator[lsst.daf.butler.Butler]:
        """Return a Butler instance for each configured repository."""
        for repository in self.repositories:
            yield self.get_butler(repository)
