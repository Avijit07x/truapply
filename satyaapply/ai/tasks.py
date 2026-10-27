from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor

from satyaapply.ai import job_prompts, prompts
from satyaapply.ai.client import Model, Request, ask
from satyaapply.ai.replies import (
    ClaimReview,
    FoundPostings,
    LatexRewrite,
    Pong,
    Posting,
    ProfileDraft,
    Score,
    StructuredRewrite,
)
from satyaapply.core.documents import ResumeData, ResumeDocument
from satyaapply.core.errors import AIError, UsageLimitError
from satyaapply.core.forms import Field, FormAnswers, FormContext
from satyaapply.core.models import Job
from satyaapply.core.profile import Profile

READ_TOOL = ("Read",)
WEB_SEARCH_TOOL = ("WebSearch",)
MAX_SCORE = 100


def _resume_request(prompt: str, document: ResumeDocument) -> Request:
    if document.needs_reading:
        return Request(prompt, prompts.SYSTEM, Model.SONNET, READ_TOOL, (document.path,))
    return Request(prompt, prompts.SYSTEM, Model.SONNET)


def ping() -> bool:
    return ask(Pong, Request("Reply with ok = true.", prompts.SYSTEM, Model.HAIKU)).ok


def draft_profile(document: ResumeDocument) -> ProfileDraft:
    return ask(ProfileDraft, _resume_request(prompts.profile_draft(document), document))


def convert_resume(document: ResumeDocument) -> ResumeData:
    return ask(ResumeData, _resume_request(prompts.resume_conversion(document), document))


def rewrite_latex(preamble: str, body: str, job: Job, notes: Sequence[str]) -> LatexRewrite:
    request = Request(prompts.latex_rewrite(preamble, body, job, notes), prompts.SYSTEM)
    return ask(LatexRewrite, request)


def rewrite_structured(resume: ResumeData, job: Job, notes: Sequence[str]) -> StructuredRewrite:
    request = Request(prompts.structured_rewrite(resume, job, notes), prompts.SYSTEM)
    return ask(StructuredRewrite, request)


def revise_latex(
    preamble: str, body: str, tailored_body: str, problems: Sequence[str]
) -> LatexRewrite:
    prompt = prompts.latex_revision(preamble, body, tailored_body, problems)
    return ask(LatexRewrite, Request(prompt, prompts.SYSTEM))


def revise_structured(
    original: ResumeData, tailored: ResumeData, problems: Sequence[str]
) -> StructuredRewrite:
    prompt = prompts.structured_revision(original, tailored, problems)
    return ask(StructuredRewrite, Request(prompt, prompts.SYSTEM))


def review_claims(original: str, tailored: str) -> tuple[str, ...]:
    request = Request(prompts.claim_review(original, tailored), prompts.SYSTEM, Model.SONNET)
    return ask(ClaimReview, request).new_claims


def score_job(
    profile: Profile, resume_text: str, job: Job, preferences: Sequence[str] = ()
) -> Score:
    prompt = job_prompts.scoring(profile, resume_text, job, preferences)
    request = Request(prompt, prompts.SYSTEM, Model.HAIKU)
    verdict = ask(Score, request)
    return Score(
        min(max(verdict.score, 0), MAX_SCORE),
        verdict.reason,
        verdict.dealbreaker,
        verdict.forbids_ai,
    )


def _search(profile: Profile, hosts: str) -> tuple[str, ...]:
    request = Request(
        job_prompts.board_search(profile, hosts), prompts.SYSTEM, Model.SONNET, WEB_SEARCH_TOOL
    )
    return ask(FoundPostings, request).urls


def find_posting_urls(profile: Profile) -> tuple[str, ...]:
    with ThreadPoolExecutor(len(job_prompts.SEARCH_HOSTS)) as pool:
        searches = [pool.submit(_search, profile, hosts) for hosts in job_prompts.SEARCH_HOSTS]
    found: list[str] = []
    failed: list[AIError] = []
    for search in searches:
        try:
            found.extend(search.result())
        except UsageLimitError:
            raise
        except AIError as error:
            failed.append(error)
    if failed and not found:
        raise failed[0]
    return tuple(dict.fromkeys(found))


def answer_fields(context: FormContext, fields: Sequence[Field]) -> FormAnswers:
    request = Request(job_prompts.form_answers(context, fields), prompts.SYSTEM, Model.SONNET)
    return ask(FormAnswers, request)


def read_posting(page_text: str) -> Posting:
    request = Request(job_prompts.posting_reading(page_text), prompts.SYSTEM, Model.HAIKU)
    return ask(Posting, request)
