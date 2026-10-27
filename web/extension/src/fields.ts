import type { Field, Kind } from "./messages";
import { SITE_SEARCH_BOXES } from "./sites";

export const FIELD_ATTR = "data-satya-field";
export const OPTION_ATTR = "data-satya-option";
const CONTROLS = "input, select, textarea, [contenteditable='true']";
const TOGGLES = "button[aria-pressed]";
const SKIPPED_TYPES = new Set([
  "hidden",
  "submit",
  "button",
  "image",
  "reset",
  "search",
  "password",
]);
const TYPED_KINDS = new Set(["email", "tel", "number", "url", "date", "file", "radio", "checkbox"]);
const MAX_LABEL = 400;
const STAR = /^["']\s*[*✱]\s*["']$/;
const REQUIRED_MARK = /[*✱](\s|$)/;
const REQUIRED_CLASS = /(^|[\s_-])required/i;
const AUTOFILL = /\bauto-?fill/i;
const PLACEHOLDER = /placeholder/i;
const NON_LABEL_TAGS = new Set([
  "INPUT",
  "SELECT",
  "TEXTAREA",
  "OPTION",
  "BUTTON",
  "SCRIPT",
  "STYLE",
  "SVG",
  "NOSCRIPT",
]);

type Control = HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement | HTMLElement;

export const clean = (text: string | null | undefined) => (text ?? "").replace(/\s+/g, " ").trim();

export const isShown = (element: Element | null): boolean => {
  if (!element?.isConnected) return false;
  const style = getComputedStyle(element);
  if (style.display === "none" || style.visibility === "hidden") return false;
  const box = element.getBoundingClientRect();
  return box.width > 0 && box.height > 0;
};

const isNotText = (element: Element) =>
  NON_LABEL_TAGS.has(element.tagName.toUpperCase()) ||
  element.getAttribute("role") === "listbox" ||
  PLACEHOLDER.test(element.getAttribute("class") ?? "");

const starAt = (element: Element, place: string) =>
  STAR.test(getComputedStyle(element, place).content) ? " * " : "";

export const textOf = (node: Element | null): string => {
  if (!node) return "";
  const parts: string[] = [];
  const walk = (element: Element) => {
    parts.push(starAt(element, "::before"));
    for (const child of element.childNodes) {
      if (child.nodeType === Node.TEXT_NODE) parts.push(child.textContent ?? "");
      if (!(child instanceof Element) || isNotText(child)) continue;
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

const byIds = (ids: string | null) =>
  clean(
    (ids ?? "")
      .split(/\s+/)
      .map((id) => textOf(id ? document.getElementById(id) : null))
      .join(" "),
  );

const nearbyText = (element: Element) => {
  let node = element.parentElement;
  for (let depth = 0; node && depth < 4; depth += 1, node = node.parentElement) {
    const text = textOf(node);
    if (text) return text.length <= MAX_LABEL ? text : "";
  }
  return "";
};

const labelsOf = (element: Element): HTMLLabelElement[] =>
  element instanceof HTMLInputElement ||
  element instanceof HTMLSelectElement ||
  element instanceof HTMLTextAreaElement
    ? [...(element.labels ?? [])]
    : [];

const labelOf = (element: Element) =>
  (
    byIds(element.getAttribute("aria-labelledby")) ||
    textOf(labelsOf(element)[0] ?? null) ||
    clean(element.getAttribute("aria-label")) ||
    nearbyText(element) ||
    clean(element.getAttribute("placeholder") ?? element.getAttribute("name"))
  ).slice(0, MAX_LABEL);

const fileLabel = (element: Element) => {
  const group = element.closest("[role='group'][aria-labelledby]");
  const name = group ? byIds(group.getAttribute("aria-labelledby")) : "";
  return clean(`${name} ${labelOf(element)}`).slice(0, MAX_LABEL);
};

const optionLabel = (input: Element) =>
  textOf(labelsOf(input)[0] ?? null) ||
  clean(input.getAttribute("aria-label")) ||
  clean(input instanceof HTMLInputElement ? input.value : input.textContent);

const groupLabel = (inputs: Element[]) => {
  const first = inputs[0];
  if (!first) return "";
  const holder = first.closest("fieldset, [role='radiogroup'], [role='group']");
  if (holder) {
    const legend = holder.querySelector("legend");
    const named =
      byIds(holder.getAttribute("aria-labelledby")) ||
      textOf(legend) ||
      clean(holder.getAttribute("aria-label"));
    if (named) return named.slice(0, MAX_LABEL);
  }
  const options = inputs.map(optionLabel).filter(Boolean);
  let node = first.parentElement;
  for (let depth = 0; node && depth < 6; depth += 1, node = node.parentElement) {
    const around = node;
    if (!inputs.every((input) => around.contains(input))) continue;
    let text = textOf(around);
    options.forEach((option) => (text = text.replace(option, " ")));
    text = clean(text);
    if (text) return text.slice(0, MAX_LABEL);
  }
  return clean(first.getAttribute("name"));
};

const kindOf = (element: Control): Kind | null => {
  const tag = element.tagName.toLowerCase();
  if (tag === "select") return "select";
  if (tag === "textarea" || (tag !== "input" && element.isContentEditable)) return "textarea";
  const type = (element.getAttribute("type") ?? "text").toLowerCase();
  if (SKIPPED_TYPES.has(type)) return null;
  if (
    element.matches(SITE_SEARCH_BOXES) ||
    element.getAttribute("role") === "combobox" ||
    element.getAttribute("aria-autocomplete") === "list"
  ) {
    return "combobox";
  }
  return TYPED_KINDS.has(type) ? (type as Kind) : "text";
};

const controlCount = (node: Element) => node.querySelectorAll(CONTROLS).length;

const shownChoice = (element: Element) => {
  let node = element.parentElement;
  for (let depth = 0; node && depth < 2; depth += 1, node = node.parentElement) {
    if (controlCount(node) > 1 || node.querySelector("label, legend")) return "";
    const text = textOf(node);
    if (text) return text;
  }
  return "";
};

const valueOf = (element: Control, kind: Kind) => {
  if (element instanceof HTMLSelectElement) {
    const picked = element.options[element.selectedIndex];
    return element.value && picked ? clean(picked.textContent) : "";
  }
  if (element instanceof HTMLInputElement && kind === "file") return element.files?.[0]?.name ?? "";
  if (element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement) {
    return element.value || (kind === "combobox" ? shownChoice(element) : "");
  }
  return clean(element.textContent);
};

const markedRequired = (element: Element) => {
  const holder = element.closest("[class*='field'], [class*='question'], fieldset, li");
  const title = holder?.querySelector("label, legend, [class*='title']");
  return !!title && REQUIRED_CLASS.test(title.getAttribute("class") ?? "");
};

const isRequired = (element: Element, label: string) =>
  (element instanceof HTMLInputElement ||
  element instanceof HTMLSelectElement ||
  element instanceof HTMLTextAreaElement
    ? element.required
    : false) ||
  element.getAttribute("aria-required") === "true" ||
  REQUIRED_MARK.test(label) ||
  markedRequired(element);

const pickScope = (): Element => {
  const dialogs = [
    ...document.querySelectorAll("[role='dialog'], dialog[open], [aria-modal='true']"),
  ].filter((dialog) => isShown(dialog) && controlCount(dialog));
  const last = dialogs[dialogs.length - 1];
  if (last) return last;
  const forms = [...document.querySelectorAll("form")].filter((form) => controlCount(form));
  forms.sort((a, b) => controlCount(b) - controlCount(a));
  return forms[0] ?? document.body;
};

let nextId = 0;
const idFor = (element: Element) => {
  const existing = element.getAttribute(FIELD_ATTR);
  if (existing) return existing;
  nextId += 1;
  return `f${String(nextId)}`;
};

const disabled = (element: Control) => "disabled" in element && element.disabled;
const readOnly = (element: Control) => "readOnly" in element && element.readOnly;

const toggleGroups = (scope: Element) => {
  const groups = new Map<Element, HTMLElement[]>();
  for (const button of scope.querySelectorAll<HTMLElement>(TOGGLES)) {
    const parent = button.parentElement;
    if (!parent || !isShown(button)) continue;
    groups.set(parent, [...(groups.get(parent) ?? []), button]);
  }
  return [...groups.values()].filter((buttons) => buttons.length > 1);
};

const grouped = (id: string, kind: Kind, inputs: HTMLElement[], label: string): Field => {
  inputs.forEach((input, index) => {
    input.setAttribute(FIELD_ATTR, id);
    input.setAttribute(OPTION_ATTR, String(index));
  });
  const picked = (input: HTMLElement) =>
    input instanceof HTMLInputElement
      ? input.checked
      : input.getAttribute("aria-pressed") === "true";
  return {
    id,
    kind,
    label,
    required: inputs.some((input) => isRequired(input, label)),
    options: inputs.map(optionLabel),
    value: inputs.filter(picked).map(optionLabel).join(" | "),
    max_length: null,
  };
};

export function readFields(): Field[] {
  const scope = pickScope();
  const fields: Field[] = [];
  const groups = new Map<string, { kind: Kind; inputs: HTMLInputElement[] }>();
  for (const element of scope.querySelectorAll<Control>(CONTROLS)) {
    const kind = kindOf(element);
    if (!kind || disabled(element) || element.getAttribute("aria-hidden") === "true") continue;
    if (element instanceof HTMLInputElement && (kind === "radio" || kind === "checkbox")) {
      if (!isShown(element) && !labelsOf(element).some(isShown)) continue;
      const name = element.getAttribute("name") ?? `__single_${String(groups.size)}`;
      const group = groups.get(name) ?? { kind, inputs: [] };
      group.inputs.push(element);
      groups.set(name, group);
      continue;
    }
    if (kind !== "file" && (!isShown(element) || readOnly(element))) continue;
    const label = kind === "file" ? fileLabel(element) : labelOf(element);
    if (kind === "file" && AUTOFILL.test(label)) continue;
    const id = idFor(element);
    element.setAttribute(FIELD_ATTR, id);
    const options =
      element instanceof HTMLSelectElement
        ? [...element.options]
            .filter((option) => !option.disabled && option.value !== "")
            .map((option) => clean(option.textContent))
        : [];
    fields.push({
      id,
      kind,
      label,
      required: isRequired(element, label),
      options,
      value: valueOf(element, kind),
      max_length:
        element instanceof HTMLInputElement && element.maxLength > 0 ? element.maxLength : null,
    });
  }
  for (const { kind, inputs } of groups.values()) {
    const [first] = inputs;
    if (!first) continue;
    const id = idFor(first);
    if (kind === "checkbox" && inputs.length === 1) {
      first.setAttribute(FIELD_ATTR, id);
      first.setAttribute(OPTION_ATTR, "0");
      const label = labelOf(first);
      fields.push({
        id,
        kind: "checkbox",
        label,
        required: isRequired(first, label),
        options: [],
        value: first.checked ? "yes" : "",
        max_length: null,
      });
      continue;
    }
    fields.push(grouped(id, kind === "radio" ? "radio" : "checkboxes", inputs, groupLabel(inputs)));
  }
  for (const buttons of toggleGroups(scope)) {
    const [first] = buttons;
    if (first) fields.push(grouped(idFor(first), "radio", buttons, groupLabel(buttons)));
  }
  return fields;
}

export const controlsOf = (id: string) => [
  ...document.querySelectorAll<HTMLElement>(`[${FIELD_ATTR}="${id}"]`),
];

export const optionOf = (id: string, index: number) =>
  document.querySelector<HTMLElement>(`[${FIELD_ATTR}="${id}"][${OPTION_ATTR}="${String(index)}"]`);
