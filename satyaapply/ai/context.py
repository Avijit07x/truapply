import json

from satyaapply.core.codec import encode
from satyaapply.core.profile import CoverLetter, Profile, UnknownQuestions

PREFER_NOT = "Prefer not to say"


def _places(profile: Profile) -> str:
    places = profile.work_places
    accepted = [
        f"on-site or hybrid in {profile.city}" if places.onsite_city else "",
        f"remote within {profile.country}" if places.remote_country else "",
        (
            f"relocating within {profile.country}"
            + (f" to {', '.join(places.relocate_cities)}" if places.relocate_cities else "")
        )
        if places.relocate
        else "",
        "remote for companies abroad (without moving)" if places.remote_abroad else "",
    ]
    return "; ".join(item for item in accepted if item) or "not stated"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def candidate_summary(profile: Profile) -> str:
    salary = profile.salary
    wanted = f"{salary.expected_min:,}-{salary.expected_max:,}"
    return "\n".join(
        [
            f"Target roles: {', '.join(profile.roles)}",
            f"Experience: {profile.years_experience:g} years",
            f"Based in: {profile.city}, {profile.country}",
            f"Will work: {_places(profile)}",
            f"Can work without a visa in: {', '.join(profile.work_without_visa)}",
            f"Needs visa sponsorship elsewhere: {_yes_no(profile.needs_sponsorship_elsewhere)}",
            f"Yearly salary wanted: {wanted} {salary.currency}",
            f"Notice period: {profile.notice_period}",
        ]
    )


def _diversity(profile: Profile) -> dict[str, str]:
    if profile.diversity is None:
        return {
            "gender": PREFER_NOT,
            "disability": PREFER_NOT,
            "veteran": PREFER_NOT,
            "ethnicity": PREFER_NOT,
        }
    data = encode(profile.diversity)
    return data if isinstance(data, dict) else {}


def candidate_facts(profile: Profile) -> str:
    first, _, last = profile.name.partition(" ")
    facts = {
        "full_name": profile.name,
        "first_name": first,
        "last_name": last or first,
        "email": profile.email,
        "phone": profile.phone,
        "city": profile.city,
        "country": profile.country,
        "links": list(profile.links),
        "current_company": profile.current_company,
        "years_experience": profile.years_experience,
        "notice_period": profile.notice_period,
        "citizenship": profile.citizenship,
        "can_work_without_visa_in": list(profile.work_without_visa),
        "needs_sponsorship_elsewhere": profile.needs_sponsorship_elsewhere,
        "will_work": _places(profile),
        "salary": encode(profile.salary),
        "date_of_birth": profile.dob.isoformat() if profile.dob else None,
        "diversity": _diversity(profile),
        "other_true_facts": profile.extra_facts,
    }
    return json.dumps(facts, ensure_ascii=False, indent=1)


def unknown_rule(profile: Profile) -> str:
    if profile.unknown_questions is UnknownQuestions.GUESS:
        return "give the most reasonable answer consistent with the facts and set `guessed` = true"
    return "leave it unanswered and list it in `unknown` with `legal` = false"


def cover_letter_rule(profile: Profile) -> str:
    rules = {
        CoverLetter.REQUIRED: "write one only when the form requires a cover letter",
        CoverLetter.ALWAYS: "write one whenever the form has a cover letter field",
        CoverLetter.NEVER: "never write one; if the form requires one, set `skip_reason`",
    }
    return rules[profile.cover_letter]
