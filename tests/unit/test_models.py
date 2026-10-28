from truapply.core.models import Job, Source, make_dupe_key, normalize_company


def test_legal_suffixes_are_dropped_from_company_names() -> None:
    assert normalize_company("Acme Technologies Pvt. Ltd.") == "acme technologies"


def test_a_company_named_only_by_a_suffix_word_is_kept() -> None:
    assert normalize_company("Co") == "co"


def test_same_job_on_two_sites_shares_a_dupe_key() -> None:
    assert make_dupe_key("Acme, Inc.", "Frontend Engineer (React)") == make_dupe_key(
        "ACME", "Frontend Engineer - React"
    )


def test_different_titles_have_different_dupe_keys() -> None:
    assert make_dupe_key("Acme", "Frontend Engineer") != make_dupe_key("Acme", "Backend Engineer")


def test_job_key_combines_source_and_id() -> None:
    job = Job(Source.LINKEDIN, "123", "https://example.com", "Acme", "Developer")
    assert job.key == "linkedin:123"
