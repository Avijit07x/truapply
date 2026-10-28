import re
from collections.abc import Callable

from truapply.core.profile import Profile
from truapply.store.answers import question_key

Fact = Callable[[Profile], str]


def _first(profile: Profile) -> str:
    return profile.name.split()[0] if profile.name.split() else ""


def _last(profile: Profile) -> str:
    return " ".join(profile.name.split()[1:])


def _link(site: str) -> Fact:
    return lambda profile: next((link for link in profile.links if site in link.lower()), "")


def _years(profile: Profile) -> str:
    return f"{profile.years_experience:g}"


FACTS: tuple[tuple[re.Pattern[str], Fact], ...] = (
    (re.compile(r"(full |your )?(legal )?name"), lambda profile: profile.name),
    (re.compile(r"(legal |preferred )?first name|given name"), _first),
    (re.compile(r"(legal )?last name|surname|family name"), _last),
    (re.compile(r"(confirm )?(your )?e ?mail( address)?"), lambda profile: profile.email),
    (re.compile(r"(phone|mobile|contact)( number)?"), lambda profile: profile.phone),
    (re.compile(r"linkedin( profile)?( url)?"), _link("linkedin.com")),
    (re.compile(r"github( profile)?( url)?"), _link("github.com")),
    (
        re.compile(r"(current|most recent) (company|employer)"),
        lambda profile: profile.current_company,
    ),
    (re.compile(r"(current )?(city|location)( city)?"), lambda profile: profile.city),
    (
        re.compile(
            r"(current )?country( of residence)?|which country are you (currently )?based in"
        ),
        lambda profile: profile.country,
    ),
    (re.compile(r"nationality|citizenship"), lambda profile: profile.citizenship),
    (re.compile(r"notice period"), lambda profile: profile.notice_period),
    (re.compile(r"(total )?years of (professional )?experience"), _years),
)


def profile_fact(profile: Profile, label: str) -> str:
    key = question_key(label)
    return next((fact(profile) for pattern, fact in FACTS if pattern.fullmatch(key)), "")
