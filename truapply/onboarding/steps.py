from dataclasses import dataclass
from datetime import date

from truapply.ai.replies import ProfileDraft
from truapply.core.models import normalize_company
from truapply.core.profile import (
    NOTICE_PERIODS,
    CoverLetter,
    Diversity,
    Salary,
    UnknownQuestions,
    WorkPlaces,
    currency_for,
)
from truapply.onboarding import ask
from truapply.onboarding.ask import Option

PREFER_NOT = "Prefer not to say"


@dataclass(frozen=True)
class Basics:
    name: str
    email: str
    phone: str
    city: str
    country: str
    links: tuple[str, ...]
    current_company: str
    years_experience: float


@dataclass(frozen=True)
class Targets:
    roles: tuple[str, ...]
    title_keywords: tuple[str, ...]
    title_exclude: tuple[str, ...]
    work_places: WorkPlaces


@dataclass(frozen=True)
class Autonomy:
    unknown_questions: UnknownQuestions
    daily_cap: int | None
    cover_letter: CoverLetter
    skip_companies: tuple[str, ...]


@dataclass(frozen=True)
class Facts:
    notice_period: str
    citizenship: str
    work_without_visa: tuple[str, ...]
    needs_sponsorship_elsewhere: bool
    salary: Salary
    dob: date | None


def _years(default: float) -> float:
    while True:
        answer = ask.text("Years of professional experience", f"{default:g}")
        try:
            return float(answer)
        except ValueError:
            ask.say("Type a number, like 2.5.")


def confirm_basics(draft: ProfileDraft) -> Basics:
    ask.heading("About you")
    ask.say("Filled in from your resume. Press Enter to keep a value, or type a new one.")
    return Basics(
        name=ask.text("Full name", draft.name, required=True),
        email=ask.text("Email", draft.email, required=True),
        phone=ask.text("Phone", draft.phone),
        city=ask.text("City", draft.city, required=True),
        country=ask.text("Country", draft.country, required=True),
        links=ask.items("Links", draft.links),
        current_company=ask.text("Current company (Enter if none)", draft.current_company),
        years_experience=_years(draft.years_experience),
    )


def ask_targets(draft: ProfileDraft, basics: Basics) -> Targets:
    ask.heading("What jobs to look for")
    roles = ask.items("Target job titles", draft.suggested_roles, required=True)
    keywords = ask.items("A job title must contain one of", draft.title_keywords, required=True)
    exclude = ask.items("Skip titles containing", draft.title_exclude)
    places = ask.choose_many(
        "Where are you willing to work?",
        [
            Option(f"On-site or hybrid in {basics.city}", "onsite"),
            Option(f"Remote within {basics.country}", "remote_country"),
            Option(f"Other cities in {basics.country} (you'd relocate)", "relocate"),
            Option("Remote for companies abroad", "remote_abroad"),
        ],
        defaults=[0, 1],
    )
    cities = ask.items("Which cities? (Enter = any city)", ()) if "relocate" in places else ()
    return Targets(
        roles,
        keywords,
        exclude,
        WorkPlaces(
            onsite_city="onsite" in places,
            remote_country="remote_country" in places,
            relocate="relocate" in places,
            relocate_cities=cities,
            remote_abroad="remote_abroad" in places,
        ),
    )


def _skip_list(current_company: str) -> tuple[str, ...]:
    default = (current_company,) if current_company else ()
    chosen = ask.items("Companies to skip", default)
    known = {normalize_company(name) for name in chosen}
    if current_company and normalize_company(current_company) not in known:
        ask.say(f"Added your current employer, {current_company}.")
        return (*chosen, current_company)
    return chosen


def ask_autonomy(current_company: str) -> Autonomy:
    ask.heading("How much it does on its own")
    ask.say("Legal and eligibility questions are never guessed, whatever you pick here.")
    ask.say("It never submits for you: you press Submit in your own Chrome.")
    unknown = ask.choose(
        "A form question your profile doesn't answer",
        [
            Option(
                "Skip the job and flag the question",
                UnknownQuestions.SKIP,
                "Your answer is saved and reused from then on.",
            ),
            Option("Best guess from your profile", UnknownQuestions.GUESS),
        ],
    )
    caps: list[Option[int | None]] = [
        Option("About 20", 20),
        Option("About 50", 50),
        Option("No limit", None),
    ]
    cap = ask.choose("Applications per day, at most (LinkedIn stays at 10 or less)", caps)
    cover = ask.choose(
        "Cover letters",
        [
            Option("Only when the form requires one", CoverLetter.REQUIRED),
            Option("Every application", CoverLetter.ALWAYS),
            Option("Never (skips jobs that require one)", CoverLetter.NEVER),
        ],
    )
    return Autonomy(unknown, cap, cover, _skip_list(current_company))


def _notice_period() -> str:
    options = [Option(period, period) for period in NOTICE_PERIODS] + [Option("Other", "")]
    chosen = ask.choose("Notice period", options)
    return chosen or ask.text("Your notice period", required=True)


def _salary(country: str) -> Salary:
    currency = ask.text("Salary currency", currency_for(country), required=True)
    lowest = ask.amount("Lowest yearly salary you'd accept (like 1200000 or 12 LPA)", True) or 1
    highest = ask.amount("Highest yearly salary you'd ask for", True, minimum=lowest) or lowest
    current = ask.amount("Current yearly salary (Enter to skip; some forms require it)", False)
    return Salary(currency.upper(), lowest, highest, current)


def ask_facts(country: str) -> Facts:
    ask.heading("Facts forms ask for")
    notice = _notice_period()
    citizenship = ask.text("Citizenship (country)", country, required=True)
    visa_free = ask.items("Countries you can work in without a visa", (citizenship,), required=True)
    sponsorship = ask.yes_no("Would you need visa sponsorship to work in other countries?", True)
    salary = _salary(country)
    dob = ask.optional_date("Date of birth (Enter to skip; some forms require it)")
    return Facts(notice, citizenship, visa_free, sponsorship, salary, dob)


def _pick(question: str, choices: tuple[str, ...]) -> str:
    return ask.choose(question, [Option(choice, choice) for choice in choices], len(choices) - 1)


def ask_diversity() -> Diversity | None:
    ask.heading("Diversity questions (optional)")
    answer_them = ask.choose(
        "How should it answer optional diversity questions?",
        [
            Option(PREFER_NOT, False),
            Option("Answer them", True),
        ],
    )
    if not answer_them:
        return None
    gender = _pick("Gender", ("Male", "Female", "Non-binary", PREFER_NOT))
    disability = _pick("Disability", ("No", "Yes", PREFER_NOT))
    ask.say("Veteran: have you served in a country's armed forces? Mostly asked by US companies.")
    veteran = _pick("Veteran", ("No", "Yes", PREFER_NOT))
    ethnicity = ask.text("Race / ethnicity (asked by US companies)", PREFER_NOT)
    return Diversity(gender, disability, veteran, ethnicity)


def ask_extra() -> str:
    ask.heading("Anything else")
    return ask.text("Anything true about you that isn't on your resume? (Enter to skip)")
