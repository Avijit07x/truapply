import { clean, controlsOf, isShown, optionOf } from "./fields";
import { bestOption } from "./match";
import type { Field } from "./messages";
import { SITE_SUGGESTIONS } from "./sites";

const MULTI_VALUE_SEPARATOR = " | ";
const MOST_CHOICES = 300;
const SUGGESTIONS = ["[role='option']", ...SITE_SUGGESTIONS].join(", ");
const MENU_MS = 400;
const SUGGESTIONS_MS = 4000;
const STEP_MS = 100;

export const sleep = (ms: number) => new Promise((done) => setTimeout(done, ms));

export function press(element: HTMLElement): void {
  const box = element.getBoundingClientRect();
  const at = {
    bubbles: true,
    cancelable: true,
    composed: true,
    button: 0,
    clientX: box.x + Math.min(4, box.width / 2),
    clientY: box.y + Math.min(4, box.height / 2),
    view: window,
  };
  for (const name of ["pointerdown", "mousedown", "pointerup", "mouseup", "click"]) {
    const Event = name.startsWith("pointer") ? PointerEvent : MouseEvent;
    const event = new Event(name, { ...at, pointerType: "mouse", isPrimary: true });
    element.dispatchEvent(event);
    if (name === "mousedown" && !event.defaultPrevented) element.focus();
  }
}

function setValue(element: HTMLInputElement | HTMLTextAreaElement, value: string): void {
  const prototype =
    element instanceof HTMLTextAreaElement
      ? HTMLTextAreaElement.prototype
      : HTMLInputElement.prototype;
  Object.getOwnPropertyDescriptor(prototype, "value")?.set?.call(element, value);
  element.dispatchEvent(
    new InputEvent("input", { bubbles: true, inputType: "insertText", data: value }),
  );
  element.dispatchEvent(new Event("change", { bubbles: true }));
}

function shownOptions(box: HTMLElement): HTMLElement[] {
  const list = document.getElementById(box.getAttribute("aria-controls") ?? "");
  const scope = list ?? document;
  return [...scope.querySelectorAll<HTMLElement>(SUGGESTIONS)].filter(isShown);
}

async function waitForOptions(box: HTMLElement, ms: number): Promise<HTMLElement[]> {
  for (let waited = 0; waited < ms; waited += STEP_MS) {
    const found = shownOptions(box);
    if (found.length) return found;
    await sleep(STEP_MS);
  }
  return [];
}

function close(box: HTMLElement): void {
  box.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  box.blur();
}

export async function readChoices(field: Field): Promise<string[]> {
  const [box] = controlsOf(field.id);
  if (!box) return [];
  press(box);
  const names = (await waitForOptions(box, MENU_MS)).map((option) => clean(option.textContent));
  close(box);
  await sleep(STEP_MS);
  return names.length <= MOST_CHOICES ? names : [];
}

async function combobox(box: HTMLElement, value: string): Promise<boolean> {
  press(box);
  let options = await waitForOptions(box, MENU_MS);
  let index = bestOption(
    options.map((option) => clean(option.textContent)),
    value,
  );
  if (index === null && box instanceof HTMLInputElement) {
    setValue(box, value);
    const key = value.slice(-1);
    box.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
    box.dispatchEvent(new KeyboardEvent("keyup", { key, bubbles: true }));
    await waitForOptions(box, SUGGESTIONS_MS);
    await sleep(MENU_MS);
    options = shownOptions(box);
    index = bestOption(
      options.map((option) => clean(option.textContent)),
      value,
    );
  }
  const option = index === null ? undefined : options[index];
  if (option) press(option);
  else close(box);
  await sleep(STEP_MS);
  return option !== undefined;
}

function choose(element: HTMLElement | null, on = true): boolean {
  if (!element) return false;
  const picked =
    element instanceof HTMLInputElement
      ? element.checked
      : element.getAttribute("aria-pressed") === "true";
  if (picked !== on) {
    if (element instanceof HTMLInputElement) element.click();
    else press(element);
  }
  return true;
}

function select(element: HTMLSelectElement, value: string): boolean {
  const options = [...element.options].filter((option) => !option.disabled && option.value !== "");
  const index = bestOption(
    options.map((option) => clean(option.textContent)),
    value,
  );
  const option = index === null ? undefined : options[index];
  if (!option) return false;
  Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value")?.set?.call(
    element,
    option.value,
  );
  element.dispatchEvent(new Event("input", { bubbles: true }));
  element.dispatchEvent(new Event("change", { bubbles: true }));
  return true;
}

function attach(element: HTMLInputElement, file: File): boolean {
  const files = new DataTransfer();
  files.items.add(file);
  element.files = files.files;
  element.dispatchEvent(new Event("input", { bubbles: true }));
  element.dispatchEvent(new Event("change", { bubbles: true }));
  return true;
}

const DIAL_CODE = /[+]\d{1,4}/;
const ROW_DEPTH = 6;
const MOST_ROW_CONTROLS = 8;
const CONTROLS = "input, select, button, [role='combobox']";

function shownDialCode(phone: HTMLElement): string {
  let row = phone.parentElement;
  for (let depth = 0; row && depth < ROW_DEPTH; depth += 1, row = row.parentElement) {
    if (row.querySelectorAll(CONTROLS).length > MOST_ROW_CONTROLS) return "";
    const code = DIAL_CODE.exec(row.innerText)?.[0];
    if (code) return code;
  }
  return "";
}

function withoutShownCode(phone: HTMLElement, value: string): string {
  const code = shownDialCode(phone);
  const trimmed = value.trim();
  return code && trimmed.startsWith(code) ? trimmed.slice(code.length).trim() : value;
}

function text(element: HTMLElement, value: string): boolean {
  element.focus();
  if (element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement) {
    setValue(element, value);
  } else {
    element.textContent = value;
    element.dispatchEvent(new InputEvent("input", { bubbles: true }));
  }
  element.blur();
  return true;
}

export async function fillField(field: Field, value: string, resume: () => Promise<File | null>) {
  const [element] = controlsOf(field.id);
  if (!element) return false;
  switch (field.kind) {
    case "select":
      return element instanceof HTMLSelectElement && select(element, value);
    case "combobox":
      return combobox(element, value);
    case "radio":
      return choose(optionOf(field.id, bestOption(field.options, value) ?? -1));
    case "checkboxes":
      return value
        .split(MULTI_VALUE_SEPARATOR)
        .map((part) => choose(optionOf(field.id, bestOption(field.options, part) ?? -1)))
        .some(Boolean);
    case "checkbox":
      return choose(element, value === "yes");
    case "file": {
      const file = await resume();
      return element instanceof HTMLInputElement && file !== null && attach(element, file);
    }
    case "tel":
      return text(element, withoutShownCode(element, value));
    default:
      return text(element, value);
  }
}

const RETYPED = new Set(["text", "email", "tel", "url", "number", "date"]);
const TYPED_KINDS = new Set([
  "text",
  "email",
  "tel",
  "url",
  "number",
  "date",
  "textarea",
  "select",
]);

function leave(element: HTMLElement): void {
  element.dispatchEvent(new FocusEvent("blur"));
  element.dispatchEvent(new FocusEvent("focusout", { bubbles: true }));
}

function retype(element: HTMLInputElement | HTMLTextAreaElement): void {
  const value = element.type === "tel" ? withoutShownCode(element, element.value) : element.value;
  if (!value) return;
  setValue(element, "");
  setValue(element, value);
  leave(element);
}

export function recommit(field: Field): void {
  if (!TYPED_KINDS.has(field.kind)) return;
  for (const element of controlsOf(field.id)) {
    if (element instanceof HTMLTextAreaElement) retype(element);
    else if (element instanceof HTMLInputElement && RETYPED.has(element.type)) retype(element);
    else if (element instanceof HTMLSelectElement) {
      element.dispatchEvent(new Event("change", { bubbles: true }));
    }
  }
}
