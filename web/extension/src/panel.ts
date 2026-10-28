import type { Job } from "./messages";

const STYLE = `
:host { all: initial; }
.panel { position: fixed; right: 16px; bottom: 16px; z-index: 2147483647; width: 320px;
  font: 13px/1.45 system-ui, sans-serif; color: #1c1c1c; background: #fff;
  border: 1px solid #d4d4d4; border-radius: 8px; box-shadow: 0 6px 24px rgb(0 0 0 / 0.14);
  padding: 12px 14px; max-height: calc(100vh - 32px); overflow-y: auto; box-sizing: border-box; }
.top { display: flex; align-items: center; gap: 8px; margin: 0 0 2px; }
.name { font-weight: 600; margin: 0; flex: 1; }
.score { font-size: 12px; font-weight: 600; padding: 1px 7px; border-radius: 999px;
  background: #eef6ee; color: #1f6b2e; }
.close { all: unset; cursor: pointer; color: #777; font-size: 16px; line-height: 1; padding: 2px 4px; }
.close:hover { color: #1c1c1c; }
.job { color: #555; margin: 0 0 10px; }
.status { display: flex; align-items: flex-start; gap: 8px; margin: 0; }
.spinner { flex: none; width: 12px; height: 12px; margin-top: 3px; border-radius: 50%;
  border: 2px solid currentColor; border-right-color: transparent;
  animation: spin 0.8s linear infinite; opacity: 0.7; }
.spinner[hidden], .score[hidden] { display: none; }
.time { color: #777; font-variant-numeric: tabular-nums; white-space: nowrap; }
ul { margin: 8px 0 0; padding: 0 4px 0 18px; max-height: calc(4 * (2 * 1.45em + 6px));
  overflow-y: auto; overscroll-behavior: contain; scrollbar-width: thin;
  scrollbar-color: #b5b5b5 transparent; }
li { margin: 0; padding: 3px 0; }
.label { display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2;
  overflow: hidden; }
li::marker { color: #d49b00; }
.why { color: #666; }
.action { margin-top: 10px; font: inherit; padding: 5px 12px; border-radius: 6px;
  border: 1px solid #1c1c1c; background: #1c1c1c; color: #fff; cursor: pointer; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .spinner { animation-duration: 2.4s; } }
@media (prefers-color-scheme: dark) {
  .panel { color: #ececec; background: #1f1f1f; border-color: #3a3a3a; }
  .job, .why, .time, .close { color: #a8a8a8; }
  .close:hover { color: #ececec; }
  .score { background: #22382a; color: #8fd19e; }
  .action { background: #ececec; color: #1c1c1c; border-color: #ececec; }
  ul { scrollbar-color: #5a5a5a transparent; }
}`;

const SECOND_MS = 1000;
const SHOW_TIME_AFTER_S = 2;

export type Panel = {
  show(job: Job): void;
  say(text: string): void;
  wait(text: string): void;
  list(items: { label: string; why: string }[]): void;
  offer(text: string, act: () => void): void;
};

const hosts: HTMLElement[] = [];

export function stayOnPage(restore: () => void): void {
  new MutationObserver(() => {
    for (const host of hosts) if (!host.isConnected) document.documentElement.append(host);
    restore();
  }).observe(document, { childList: true, subtree: true, attributes: true });
}

const element = <K extends keyof HTMLElementTagNameMap>(tag: K, className = "") => {
  const made = document.createElement(tag);
  made.className = className;
  return made;
};

export function openPanel(job: Job | null): Panel {
  const host = document.createElement("truapply-panel");
  hosts.push(host);
  const root = host.attachShadow({ mode: "open" });
  const style = element("style");
  style.textContent = STYLE;
  const box = element("div", "panel");
  const top = element("div", "top");
  const name = element("p", "name");
  name.textContent = "TruApply";
  const score = element("span", "score");
  score.hidden = true;
  const close = element("button", "close");
  close.type = "button";
  close.textContent = "×";
  close.setAttribute("aria-label", "Hide TruApply");
  close.addEventListener("click", () => {
    hosts.splice(hosts.indexOf(host), 1);
    host.remove();
  });
  top.append(name, score, close);
  const about = element("p", "job");
  const status = element("p", "status");
  const spinner = element("span", "spinner");
  spinner.hidden = true;
  const text = element("span");
  const time = element("span", "time");
  status.append(spinner, text, time);
  const items = element("ul");
  box.append(top, about, status, items);
  root.append(style, box);
  document.documentElement.append(host);

  let timer = 0;
  const stopTimer = () => {
    window.clearInterval(timer);
    time.textContent = "";
    spinner.hidden = true;
  };
  const describe = (shown: Job) => {
    about.textContent = `${shown.company} · ${shown.title}`;
    score.textContent = shown.score === null ? "" : `score ${String(shown.score)}`;
    score.hidden = shown.score === null;
  };
  if (job) describe(job);
  return {
    show: describe,
    say(said) {
      stopTimer();
      text.textContent = said;
    },
    wait(said) {
      stopTimer();
      text.textContent = said;
      spinner.hidden = false;
      const started = Date.now();
      timer = window.setInterval(() => {
        const seconds = Math.round((Date.now() - started) / SECOND_MS);
        time.textContent = seconds >= SHOW_TIME_AFTER_S ? `${String(seconds)} s` : "";
      }, SECOND_MS);
    },
    list(found) {
      items.replaceChildren(
        ...found.map(({ label, why }) => {
          const item = element("li");
          const line = element("span", "label");
          const note = element("span", "why");
          note.textContent = ` (${why})`;
          line.append(label, note);
          line.title = `${label} (${why})`;
          item.append(line);
          return item;
        }),
      );
    },
    offer(label, act) {
      const button = element("button", "action");
      button.type = "button";
      button.textContent = label;
      button.addEventListener("click", () => {
        button.remove();
        act();
      });
      box.append(button);
    },
  };
}
