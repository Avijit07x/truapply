(() => {
  const clean = (text) => (text || "").replace(/\s+/g, " ").trim();
  const scope = document.querySelector("[data-satya-scope]") || document.body;
  const shown = (node) => node.getClientRects().length > 0;
  const found = new Set();
  const messages = "[role='alert'], [aria-live='assertive'], .error, .errors, .field-error, .invalid-feedback";
  scope.querySelectorAll(messages).forEach((node) => {
    const text = clean(node.textContent);
    if (shown(node) && text) found.add(text.slice(0, 200));
  });
  scope.querySelectorAll("[aria-invalid='true']").forEach((node) => {
    const label = node.labels && node.labels.length
      ? clean(node.labels[0].textContent)
      : clean(node.getAttribute("aria-label"));
    if (label) found.add(`invalid: ${label.slice(0, 160)}`);
  });
  return [...found].slice(0, 10);
})()
