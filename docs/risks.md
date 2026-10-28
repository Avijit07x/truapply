# What-if list

Everything we expect to go wrong, how the tool notices, and what it does. **Rule:** when in doubt, stop and tell the user. Never guess, and never retry blindly.

## Job sites

| What goes wrong | How it's noticed | What the tool does | What you see |
|---|---|---|---|
| A site redesign breaks search | 0 job links on a search page, 2 runs in a row, while logged in | Site paused 24 h | Notification, and a "site broken" banner with a link to report it |
| A site redesign breaks the form | No Next/Submit button, or errors that don't go away | Job `failed`, screenshot saved. 3 failures in a row → site paused 24 h | The failed job with its screenshot |
| Block page, CAPTCHA wall, "unusual activity" | URL or text matches the site's `blocked` pattern | **Site stopped for the day immediately.** Never retried the same day. | Instant notification |
| Logged out | Redirected to a login page | Site skipped | "Run `truapply login`" in the notification and the summary |
| Job removed or closed | API 404, or "no longer accepting applications" | Job `closed` | Nothing; it's not an error |
| "Apply" leads to an unknown site | The new tab's host isn't Greenhouse, Lever or Ashby | Job `external` | The link, to apply yourself |
| Already applied (outside TruApply) | Page shows "Applied …" | Recorded as applied, skipped | Marked "applied elsewhere" |
| The same job on two sites | Same `dupe` key | Second one `skipped: duplicate` | Shown under the first one |
| Thousands of jobs found | Count after the title filter | Score at most 60 per run, newest first | Nothing |

## AI (Claude Code)

| What goes wrong | How it's noticed | What the tool does | What you see |
|---|---|---|---|
| Usage limit reached | Error from `claude` | **Run stops cleanly.** Jobs stay queued; the next run picks up. | Summary line. Instant alert if it happens two runs in a row. |
| `claude` missing or logged out | Command fails, or an auth error | Run stops | `doctor` output with the fix |
| Bad or empty reply | JSON doesn't match the schema | One retry, then that job is skipped this run | Note on the job |
| Slow or stuck | Timeout (5 min) | Same as a bad reply | Note on the job |
| Daily call budget used up | `meta.ai_calls_today` | Applying stops for the day; replies are still checked | Summary line |
| Hidden instructions in a job post | Can't be fully detected | Harmless by design: no tools, schema-checked replies | — |
| A wrong guess in best-guess mode | Can't be detected automatically | Every answer is stored in `jobs.sent` | "What was sent" on the job page |

## Resume

| What goes wrong | How it's noticed | What the tool does | What you see |
|---|---|---|---|
| Tailoring adds something false | Number check or second-AI check | **The original resume is used** | The reason, in the change view |
| Tailored resume is too long | Page count | The original is used | The reason, in the change view |
| LaTeX build fails | `pdflatex` exit code | The original `master.pdf` is used | The reason, in the change view |
| LaTeX missing | `doctor`, setup | Setup offers TinyTeX or the built-in design | Setup prompt |
| You edit your master resume | File hash changed | `master.pdf` is rebuilt on the next run | Nothing |

## Your computer

| What goes wrong | How it's noticed | What the tool does | What you see |
|---|---|---|---|
| Mac asleep or off at run time | — | launchd runs the missed job on wake | Nothing |
| Crash or power loss mid-run | Jobs still in `submitting` on the next start | **Marked `unconfirmed`, never re-submitted.** A confirmation email later turns it into `applied`. | `unconfirmed` jobs, so you can check them |
| Two runs at once | Lock file is held | Second run exits: "already running" | Log line |
| Chrome profile locked or corrupted | Launch error | Run stops | `doctor` explains (close the other Chrome window, or `truapply login` again) |
| Disk filling up with screenshots | Size of `shots/` | Screenshots older than 90 days are deleted | Nothing |

## Email

| What goes wrong | How it's noticed | What the tool does | What you see |
|---|---|---|---|
| App password revoked or wrong | IMAP login fails | Reply tracking paused; applying continues | Notification: "run `truapply email`" |
| A reply matched to the wrong job | You notice it | — | Fix the outcome on the job page |
| A reply that matches no application | No candidate found | Ignored | Nothing |
| A non-job email looks job-related | Header filter | Only the first 3,000 characters go to Claude; it can answer "not a job email" | Nothing |

## You

| What goes wrong | How it's noticed | What the tool does | What you see |
|---|---|---|---|
| Profile file edited by hand and broken | Validation on load | Run stops; nothing is applied with a bad profile | The exact field that's wrong |
| Question waiting for your answer | `needs_input` | That job waits; others continue | "Needs your answer" on the tracker, and in the summary |
| You stop using it | — | Nothing runs after `unschedule` | — |
| Auto-submit sends bad matches | 2 👎 in the last 10 auto-submitted | Auto-submit off; back to the review queue | Notification |
| A rule you typed is wrong ("skip fintech" by mistake) | Fewer jobs than usual | It follows the rule as written | Delete or edit it on "What it learned" |
| A rule asks for something unsafe ("say I know Kubernetes") | Checked when the rule is added | Refused, with the reason | A message explaining that facts come only from your resume |
