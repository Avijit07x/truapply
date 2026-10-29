# TruApply

A job-application helper that runs on your own computer.

It finds jobs that fit you, tailors your resume using only true facts, and fills in applications in your own Chrome. You check each one and press Submit.

- **Local.** Your data stays in `~/.truapply`. Nothing runs on our servers.
- **Honest.** It never adds facts to your resume and never guesses legal answers.
- **Your AI.** It uses your own [Claude Code](https://claude.com/claude-code) login.

## What you need

- Python 3.11 or newer
- Node.js 22 or newer (only to build the app once)
- Google Chrome
- Claude Code, installed and logged in (`claude` works in your terminal)

## Install

```bash
git clone https://github.com/Avijit07x/truapply.git
cd truapply
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
cd web && npm ci && npm run build && cd ..
```

## Start

```bash
truapply tracker --open
```

This opens TruApply in your browser. The first time, it walks you through setup.

## Setup (about 3 minutes)

1. **Your resume.** Upload a PDF, Word, LaTeX, Markdown or text file. Claude reads it once.
2. **Your details.** Name, contact details and the jobs to look for, filled in from your resume. Fix anything that's wrong.
3. **Rights and pay.** Work rights, notice period and salary. Only you can answer these.
4. **How it runs.** When it should run, whether to tailor your resume, and how many jobs per run.
5. **Extension.** Add the Chrome extension. The page checks that it's working.

You can change all of it later in **Settings**.

## Everyday use

1. Press **Run now**, or let it run on its own. It finds jobs, scores them and gets the good ones ready.
2. Open **Today** to see what's ready.
3. Open a job. The extension fills in the form in your Chrome.
4. Check it and press **Submit** yourself.

## Good to know

- It never solves CAPTCHAs, never ticks consent boxes and never submits on its own unless you turn on auto-submit in Settings.
- Check that everything works: `truapply doctor`
- Something stuck? The **Activity** page shows every run and what went wrong.

## More

- [How it works](docs/README.md)
- [Safety rules](docs/safety.md)
- [Contributing](docs/CONTRIBUTING.md)

License: MIT
