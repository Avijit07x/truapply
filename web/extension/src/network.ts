const BUSY = "data-satyaapply-busy";
const marker = "__satyaapplyNetwork";

type Watched = Window & { [marker]?: true };
type Send = (this: XMLHttpRequest, body?: Document | XMLHttpRequestBodyInit | null) => void;

function watch(): void {
  const page = window as Watched;
  if (page[marker]) return;
  page[marker] = true;
  let open = 0;
  const tell = () => {
    document.documentElement.setAttribute(BUSY, String(open));
  };
  const started = () => {
    open += 1;
    tell();
  };
  const ended = () => {
    open = Math.max(0, open - 1);
    tell();
  };
  const fetch = window.fetch.bind(window);
  window.fetch = (...args: Parameters<typeof fetch>) => {
    started();
    return fetch(...args).finally(ended);
  };
  const send = Object.getOwnPropertyDescriptor(XMLHttpRequest.prototype, "send")?.value as Send;
  XMLHttpRequest.prototype.send = function (this: XMLHttpRequest, body) {
    started();
    this.addEventListener("loadend", ended, { once: true });
    send.call(this, body);
  };
}

watch();
