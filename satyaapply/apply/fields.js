(() => {
  const FIELD_ATTR = "data-satya-field";
  const OPTION_ATTR = "data-satya-option";
  const SCOPE_ATTR = "data-satya-scope";
  const CONTROLS = "input, select, textarea, [contenteditable='true']";
  const SKIPPED_TYPES = new Set(["hidden", "submit", "button", "image", "reset", "search", "password"]);
  const TYPED_KINDS = new Set(["email", "tel", "number", "url", "date", "file", "radio", "checkbox"]);
  const MAX_LABEL = 400;
  const VALID_ID = /^f\d+$/;
  const STAR = /^["']\s*\*\s*["']$/;
  const REQUIRED_STAR = /\*(\s|$)/;
  const AUTOFILL = /\bauto-?fill/i;
  const PLACEHOLDER = /placeholder/i;
  const NON_LABEL_TAGS = new Set(["INPUT", "SELECT", "TEXTAREA", "OPTION", "BUTTON", "SCRIPT", "STYLE", "SVG", "NOSCRIPT"]);

  const clean = (text) => (text || "").replace(/\s+/g, " ").trim();
  const isShown = (element) => {
    if (!element || !element.isConnected) return false;
    const style = getComputedStyle(element);
    if (style.display === "none" || style.visibility === "hidden") return false;
    const box = element.getBoundingClientRect();
    return box.width > 0 && box.height > 0;
  };
  const isNotText = (element) =>
    NON_LABEL_TAGS.has(element.tagName.toUpperCase()) ||
    element.getAttribute("role") === "listbox" ||
    PLACEHOLDER.test(element.getAttribute("class") || "");
  const starAt = (element, place) => (STAR.test(getComputedStyle(element, place).content) ? " * " : "");
  const textOf = (node) => {
    if (!node) return "";
    const parts = [];
    const walk = (element) => {
      parts.push(starAt(element, "::before"));
      for (const child of element.childNodes) {
        if (child.nodeType === Node.TEXT_NODE) parts.push(child.textContent);
        if (child.nodeType !== Node.ELEMENT_NODE || isNotText(child)) continue;
        const style = getComputedStyle(child);
        if (style.display === "none" || style.visibility === "hidden") continue;
        const gap = style.display.startsWith("inline") ? "" : " ";
        parts.push(gap);
        walk(child);
        parts.push(gap);
      }
      parts.push(starAt(element, "::after"));
    };
    walk(node);
    return clean(parts.join(""));
  };
  const byIds = (ids) =>
    clean((ids || "").split(/\s+/).map((id) => textOf(document.getElementById(id))).join(" "));
  const nearbyText = (element) => {
    let node = element.parentElement;
    for (let depth = 0; node && depth < 4; depth += 1, node = node.parentElement) {
      const text = textOf(node);
      if (text) return text.length <= MAX_LABEL ? text : "";
    }
    return "";
  };
  const labelOf = (element) =>
    (byIds(element.getAttribute("aria-labelledby")) ||
      (element.labels && element.labels.length ? textOf(element.labels[0]) : "") ||
      clean(element.getAttribute("aria-label")) ||
      nearbyText(element) ||
      clean(element.getAttribute("placeholder") || element.getAttribute("name"))).slice(0, MAX_LABEL);
  const optionLabel = (input) =>
    (input.labels && input.labels.length ? textOf(input.labels[0]) : "") ||
    clean(input.getAttribute("aria-label")) ||
    clean(input.value);
  const groupLabel = (inputs) => {
    const holder = inputs[0].closest("fieldset, [role='radiogroup'], [role='group']");
    if (holder) {
      const legend = holder.querySelector("legend");
      const named =
        byIds(holder.getAttribute("aria-labelledby")) ||
        (legend ? textOf(legend) : "") ||
        clean(holder.getAttribute("aria-label"));
      if (named) return named.slice(0, MAX_LABEL);
    }
    const options = inputs.map(optionLabel).filter(Boolean);
    let node = inputs[0].parentElement;
    for (let depth = 0; node && depth < 6; depth += 1, node = node.parentElement) {
      if (!inputs.every((input) => node.contains(input))) continue;
      let text = textOf(node);
      options.forEach((option) => { text = text.replace(option, " "); });
      text = clean(text);
      if (text) return text.slice(0, MAX_LABEL);
    }
    return clean(inputs[0].getAttribute("name"));
  };
  const kindOf = (element) => {
    const tag = element.tagName.toLowerCase();
    if (tag === "select") return "select";
    if (tag === "textarea" || (tag !== "input" && element.isContentEditable)) return "textarea";
    const type = (element.getAttribute("type") || "text").toLowerCase();
    if (SKIPPED_TYPES.has(type)) return null;
    if (element.getAttribute("role") === "combobox" || element.getAttribute("aria-autocomplete") === "list") {
      return "combobox";
    }
    return TYPED_KINDS.has(type) ? type : "text";
  };
  const valueOf = (element, kind) => {
    if (kind === "select") {
      return element.value && element.selectedIndex >= 0
        ? clean(element.options[element.selectedIndex].textContent)
        : "";
    }
    if (kind === "file") return element.files && element.files.length ? element.files[0].name : "";
    if (element.tagName.toLowerCase() !== "input" && element.isContentEditable) return clean(element.textContent);
    return element.value || (kind === "combobox" ? shownChoice(element) : "");
  };
  const shownChoice = (element) => {
    let node = element.parentElement;
    for (let depth = 0; node && depth < 2; depth += 1, node = node.parentElement) {
      if (controlCount(node) > 1 || node.querySelector("label, legend")) return "";
      const text = textOf(node);
      if (text) return text;
    }
    return "";
  };
  const isRequired = (element, label) =>
    element.required || element.getAttribute("aria-required") === "true" || REQUIRED_STAR.test(label);
  const controlCount = (node) => node.querySelectorAll(CONTROLS).length;
  const pickScope = () => {
    const dialogs = [...document.querySelectorAll("[role='dialog'], dialog[open], [aria-modal='true']")]
      .filter((dialog) => isShown(dialog) && controlCount(dialog));
    if (dialogs.length) return dialogs[dialogs.length - 1];
    const forms = [...document.querySelectorAll("form")].filter((form) => controlCount(form));
    forms.sort((a, b) => controlCount(b) - controlCount(a));
    return forms[0] || document.body;
  };

  window.__satyaNextId = window.__satyaNextId || 0;
  const idFor = (element) => {
    const existing = element.getAttribute(FIELD_ATTR);
    if (existing && VALID_ID.test(existing)) return existing;
    window.__satyaNextId += 1;
    return `f${window.__satyaNextId}`;
  };

  document.querySelectorAll(`[${SCOPE_ATTR}]`).forEach((node) => node.removeAttribute(SCOPE_ATTR));
  const scope = pickScope();
  scope.setAttribute(SCOPE_ATTR, "1");

  const fields = [];
  const groups = new Map();
  for (const element of scope.querySelectorAll(CONTROLS)) {
    const kind = kindOf(element);
    if (!kind || element.disabled) continue;
    if (kind === "radio" || kind === "checkbox") {
      const shown = isShown(element) || [...(element.labels || [])].some(isShown);
      if (!shown) continue;
      const name = element.getAttribute("name") || `__single_${groups.size}`;
      if (!groups.has(name)) groups.set(name, { kind, inputs: [] });
      groups.get(name).inputs.push(element);
      continue;
    }
    if (kind !== "file" && (!isShown(element) || element.readOnly)) continue;
    const label = labelOf(element);
    if (kind === "file" && AUTOFILL.test(label)) continue;
    const id = idFor(element);
    element.setAttribute(FIELD_ATTR, id);
    const options = kind === "select"
      ? [...element.options].filter((option) => !option.disabled && option.value !== "").map((option) => clean(option.textContent))
      : [];
    fields.push({
      id, kind, label, required: isRequired(element, label), options,
      value: valueOf(element, kind), max_length: element.maxLength > 0 ? element.maxLength : null,
    });
  }
  for (const { kind, inputs } of groups.values()) {
    const id = idFor(inputs[0]);
    const single = kind === "checkbox" && inputs.length === 1;
    inputs.forEach((input, index) => {
      input.setAttribute(FIELD_ATTR, id);
      input.setAttribute(OPTION_ATTR, String(index));
    });
    const label = single ? labelOf(inputs[0]) : groupLabel(inputs);
    fields.push({
      id,
      kind: single ? "checkbox" : kind === "radio" ? "radio" : "checkboxes",
      label,
      required: inputs.some((input) => isRequired(input, label)),
      options: single ? [] : inputs.map(optionLabel),
      value: single
        ? (inputs[0].checked ? "yes" : "")
        : inputs.filter((input) => input.checked).map(optionLabel).join(" | "),
      max_length: null,
    });
  }
  return fields;
})()
