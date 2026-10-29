# What-if list

Everything we expect to go wrong, how the tool notices, and what it does. **Rule:** when in doubt, stop and tell the user. Never guess, and never retry blindly.

## Job sites and forms

| What goes wrong | How it's noticed | What the tool does | What you see |
|---|---|---|---|
| A site changes its form | The extension can't fill a field, or a required field is still empty | Leaves it for you. Auto-submit stops before Submit. | The field outlined, and listed in the panel as left for you |
| A choice list has nothing that fits your answer | No suggestion matches | Leaves it for you | "none of its suggestions matched your answer" in the panel |
| Job removed or closed | Checked against the company's board just before tailoring | Job `closed`, not tailored | "the job was removed from the company's board or its deadline passed" on the job |
| A job page on a site TruApply doesn't know | — | Nothing, until you click the TruApply icon. Then it adds the job and fills what it can. | The panel |
| Already applied | The job is `applied` | The extension doesn't fill it again | "You applied to this job on …" in the panel |
| The same job on two sites | Same company and title as a job that's already ready or applied | Second one `skipped` | "duplicate of a job already in your queue" |
| Thousands of jobs found | Count after the title and place filters | Score at most 40 per run (`scores_per_run`), newest first. Tailor at most 5 per run (`jobs_per_run`), best score first, within your daily limit. The rest wait for the next run. | Nothing |
| Wellfound asks TruApply to slow down | "Too many requests" reply | Wellfound isn't checked again for an hour | A line in the run log |

## AI (Claude Code)

| What goes wrong | How it's noticed | What the tool does | What you see |
|---|---|---|---|
| Usage limit reached | Error from `claude` | **Run stops cleanly.** Jobs stay where they were; the next run picks up. | The reason and the fix, in the run log |
| `claude` missing or logged out | Command fails, or an auth error | Run stops | `doctor` output with the fix |
| Bad or empty reply | JSON doesn't match the schema | One retry. Then a job that wasn't scored stays new and is tried next run, a resume that wasn't tailored falls back to your original, and a form keeps what was filled from your profile. | "couldn't score it, will retry next run" in the run log, the reason on the job, or "Couldn't fill" in the panel |
| Slow or stuck | Timeout (5 min) | Same as a bad reply | Same |
| Daily call budget used up | Today's count in `meta` (`ai_calls:<date>`) reaches `ai_calls_per_day` (300) | The run stops and picks up again tomorrow | The reason, and where to raise the budget |
| Hidden instructions in a job post | Can't be fully detected | Harmless by design: no tools, schema-checked replies | — |
| A wrong guess in best-guess mode | Can't be detected automatically | You check the form before Submit. Every answer sent is stored in `jobs.sent`. | The filled answers on the job page |

## Resume

| What goes wrong | How it's noticed | What the tool does | What you see |
|---|---|---|---|
| Tailoring adds something false | Number check or second-AI check | One try to fix it, then **the original resume is used** | The reason, in the change view |
| Tailored resume is too long | Page count | The original is used | The reason, in the change view |
| LaTeX build fails | `pdflatex` exit code | The original `master.pdf` is used | The reason, in the change view |
| LaTeX missing | `doctor`, setup | Setup offers TinyTeX or the built-in design | Setup prompt |
| You edit your master resume | File hash changed | `master.pdf` is rebuilt on the next run | Nothing |

## Your computer

| What goes wrong | How it's noticed | What the tool does | What you see |
|---|---|---|---|
| Computer asleep or off at run time | — | launchd or Task Scheduler runs the missed run on wake | Nothing |
| Crash or power loss mid-run | — | Runs never submit anything, so nothing is lost. The next run carries on from where the jobs are. | Nothing |
| Crash during an auto-submit | The send isn't finished after 15 minutes | Never tried again. Not pressed yet: left for you. Pressed but not confirmed: marked unconfirmed. | A note on the job; for an unconfirmed one, check your email before applying yourself |
| Two runs at once | Lock file is held | Second run exits: "already running" | The message, with how to wait or stop the first |
| The app isn't running | The extension can't reach `127.0.0.1` | Fills nothing | "TruApply isn't running. Start it, then reload this page." in the panel |
| Chrome missing | Launch error (the app uses headless Chrome to read some pages and print PDFs) | Stops that step | `doctor` explains: install Chrome, or `playwright install chromium` |

## Email

TruApply never reads your email. It has no access to it.

## You

| What goes wrong | How it's noticed | What the tool does | What you see |
|---|---|---|---|
| Profile file edited by hand and broken | Validation on load | Run stops; nothing is prepared with a bad profile | The exact field that's wrong |
| A question it can't answer | Your profile and saved answers don't cover it, or it's a legal question | Left blank on the form | Outlined, and listed in the panel. What you type is saved for next time. |
| You stop using it | — | Nothing runs after `unschedule` | — |
| Auto-submit sends bad matches | 2 👎 in the last 10 auto-submitted | Auto-submit turns off | It shows off in Settings |
| A rule you typed is wrong ("skip fintech" by mistake) | Fewer jobs than usual | It follows the rule as written | Delete or edit it on "What it learned" |
| A rule or note asks for something false ("say I know Kubernetes") | Not checked when it's added | A rule only goes to scoring, as your preference, never as a fact. A tailoring note that leads to a new claim is caught by the resume checks, and the original resume is used. | The reason, in the change view |
