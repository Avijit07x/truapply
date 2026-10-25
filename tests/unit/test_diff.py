from satyaapply.resume.diff import changed_lines


def test_only_changed_lines_are_listed() -> None:
    original = "Name\nBuilt 40 components.\nEducation"
    tailored = "Name\nBuilt 40 shared React components.\nEducation"
    assert changed_lines(original, tailored) == [
        "-Built 40 components.",
        "+Built 40 shared React components.",
    ]


def test_identical_resumes_have_no_changes() -> None:
    assert changed_lines("a\nb", "a\nb") == []
