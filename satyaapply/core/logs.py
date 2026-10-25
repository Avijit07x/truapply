import logging

FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.WARNING,
        format=FORMAT,
        force=True,
    )
