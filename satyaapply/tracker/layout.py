from satyaapply.tracker.html import APP_NAME, FOOTER, NAV, SUBTITLE, e, page

__all__ = ["APP_NAME", "FOOTER", "NAV", "SUBTITLE", "page_title", "shell"]


def page_title(icon: str, title: str) -> str:
    return (
        f'<h1 class="page-title"><span class="page-icon" aria-hidden="true">{e(icon)}</span>'
        f"{e(title)}</h1>"
    )


def shell(title: str, body: str, active: str) -> str:
    return page(title, body, active)
