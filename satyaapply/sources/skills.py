from collections.abc import Iterable

from satyaapply.core.models import normalize

ENOUGH_SHARE = 0.6
SKILLS: tuple[tuple[str, ...], ...] = (
    ("javascript", "js"),
    ("typescript", "ts"),
    ("react", "reactjs"),
    ("next js", "nextjs"),
    ("vue", "vuejs"),
    ("nuxt",),
    ("angular",),
    ("svelte",),
    ("node", "nodejs"),
    ("express",),
    ("nestjs",),
    ("python",),
    ("django",),
    ("flask",),
    ("fastapi",),
    ("java",),
    ("spring",),
    ("kotlin",),
    ("scala",),
    ("net", "dotnet", "asp net"),
    ("php",),
    ("laravel",),
    ("ruby",),
    ("rails",),
    ("golang",),
    ("rust",),
    ("swift",),
    ("ios",),
    ("android",),
    ("flutter",),
    ("dart",),
    ("react native",),
    ("electron",),
    ("pytorch",),
    ("tensorflow",),
    ("salesforce",),
    ("shopify",),
    ("wordpress",),
    ("unity",),
)


def skills_in(texts: Iterable[str]) -> frozenset[str]:
    words = f" {normalize(' '.join(texts))} "
    return frozenset(
        names[0] for names in SKILLS if any(f" {normalize(name)} " in words for name in names)
    )


def skills_fit(asked: frozenset[str], known: frozenset[str]) -> bool:
    return not asked or len(asked & known) / len(asked) >= ENOUGH_SHARE
