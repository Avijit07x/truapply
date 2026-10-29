import { Checkbox as BaseCheckbox } from "@base-ui/react/checkbox";
import { Field } from "@base-ui/react/field";
import { Radio } from "@base-ui/react/radio";
import { RadioGroup } from "@base-ui/react/radio-group";
import { Select } from "@base-ui/react/select";
import { Switch as BaseSwitch } from "@base-ui/react/switch";
import { type ReactNode, useId, useState } from "react";
import { cx } from "../lib/cx";
import styles from "./Fields.module.css";
import { Check, ChevronDown, Close } from "./icons";
import { Info } from "./Info";

type TextFieldProps = {
  label: ReactNode;
  hint?: ReactNode;
  info?: ReactNode;
  value: string;
  onChange: (value: string) => void;
  multiline?: boolean;
  short?: boolean;
  rows?: number;
  type?: "text" | "number" | "date" | "email" | "tel";
  min?: number;
  max?: number;
  step?: number | "any";
  maxLength?: number;
  required?: boolean;
  autoFocus?: boolean;
  placeholder?: string;
};

function about(label: ReactNode): string {
  return typeof label === "string" ? label : "";
}

function Titled({
  info,
  label,
  children,
}: {
  info?: ReactNode;
  label: ReactNode;
  children: ReactNode;
}) {
  if (!info) return children;
  return (
    <div className={styles.labelRow}>
      {children}
      <Info about={about(label)}>{info}</Info>
    </div>
  );
}

export function TextField({
  label,
  hint,
  info,
  value,
  onChange,
  multiline = false,
  short = false,
  rows = 3,
  ...input
}: TextFieldProps) {
  return (
    <Field.Root className={styles.field}>
      <Titled info={info} label={label}>
        <Field.Label className={styles.label}>{label}</Field.Label>
      </Titled>
      <Field.Control
        className={cx(styles.input, short && styles.short)}
        value={value}
        onValueChange={onChange}
        render={multiline ? <textarea rows={rows} /> : undefined}
        {...input}
      />
      {hint && <Field.Description className={styles.hint}>{hint}</Field.Description>}
    </Field.Root>
  );
}

type TagsFieldProps = {
  label: ReactNode;
  hint?: ReactNode;
  info?: ReactNode;
  values: readonly string[];
  onChange: (values: string[]) => void;
  maxItems: number;
  maxLength: number;
};

function merged(values: readonly string[], typed: string): string[] {
  const kept = new Map(values.map((value) => [value.toLowerCase(), value]));
  for (const part of typed.split(",")) {
    const words = part.split(/\s+/).filter(Boolean).join(" ");
    if (words && !kept.has(words.toLowerCase())) {
      kept.set(words.toLowerCase(), words);
    }
  }
  return [...kept.values()];
}

export function TagsField({
  label,
  hint,
  info,
  values,
  onChange,
  maxItems,
  maxLength,
}: TagsFieldProps) {
  const [draft, setDraft] = useState("");
  const add = () => {
    if (draft.trim()) {
      onChange(merged(values, draft).slice(0, maxItems));
    }
    setDraft("");
  };
  return (
    <Field.Root className={styles.field}>
      <Titled info={info} label={label}>
        <Field.Label className={styles.label}>{label}</Field.Label>
      </Titled>
      <div className={cx(styles.input, styles.tags)}>
        {values.map((value) => (
          <span key={value} className={styles.tag}>
            {value}
            <button
              type="button"
              className={styles.untag}
              aria-label={`Remove ${value}`}
              onClick={() => {
                onChange(values.filter((item) => item !== value));
              }}
            >
              <Close size={10} />
            </button>
          </span>
        ))}
        <Field.Control
          className={styles.tagInput}
          value={draft}
          maxLength={maxLength}
          disabled={values.length >= maxItems}
          placeholder={values.length === 0 ? "Type, then press Enter" : undefined}
          onValueChange={setDraft}
          onBlur={add}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === ",") {
              event.preventDefault();
              add();
            } else if (event.key === "Backspace" && !draft && values.length > 0) {
              onChange(values.slice(0, -1));
            }
          }}
        />
      </div>
      {hint && <Field.Description className={styles.hint}>{hint}</Field.Description>}
    </Field.Root>
  );
}

type SelectFieldProps = {
  label: ReactNode;
  info?: ReactNode;
  value: string;
  options: readonly string[];
  onChange: (value: string) => void;
};

export function SelectField({ label, info, value, options, onChange }: SelectFieldProps) {
  return (
    <Select.Root
      value={value}
      onValueChange={(next) => {
        if (next !== null) {
          onChange(next);
        }
      }}
    >
      <div className={styles.field}>
        <Titled info={info} label={label}>
          <Select.Label className={styles.label}>{label}</Select.Label>
        </Titled>
        <Select.Trigger className={cx(styles.input, styles.trigger)}>
          <span className={styles.fit}>
            {options.map((option) => (
              <span key={option} aria-hidden="true">
                {option}
              </span>
            ))}
            <Select.Value />
          </span>
          <Select.Icon className={styles.chevron}>
            <ChevronDown size={12} />
          </Select.Icon>
        </Select.Trigger>
      </div>
      <Select.Portal>
        <Select.Positioner
          className={styles.positioner}
          sideOffset={4}
          alignItemWithTrigger={false}
        >
          <Select.Popup className={styles.popup}>
            <Select.List className={styles.list}>
              {options.map((option) => (
                <Select.Item key={option} value={option} className={styles.item}>
                  <Select.ItemIndicator className={styles.itemCheck}>
                    <Check size={12} />
                  </Select.ItemIndicator>
                  <Select.ItemText>{option}</Select.ItemText>
                </Select.Item>
              ))}
            </Select.List>
          </Select.Popup>
        </Select.Positioner>
      </Select.Portal>
    </Select.Root>
  );
}

type ToggleProps = {
  label: ReactNode;
  info?: ReactNode;
  checked: boolean;
  onChange: (checked: boolean) => void;
};

export function Checkbox({ label, info, checked, onChange }: ToggleProps) {
  return (
    <Titled info={info} label={label}>
      <label className={styles.toggle}>
        <BaseCheckbox.Root className={styles.checkbox} checked={checked} onCheckedChange={onChange}>
          <BaseCheckbox.Indicator className={styles.checkboxMark}>
            <Check size={12} />
          </BaseCheckbox.Indicator>
        </BaseCheckbox.Root>
        <span>{label}</span>
      </label>
    </Titled>
  );
}

export function Switch({ label, info, checked, onChange }: ToggleProps) {
  return (
    <Titled info={info} label={label}>
      <label className={styles.toggle}>
        <BaseSwitch.Root className={styles.switch} checked={checked} onCheckedChange={onChange}>
          <BaseSwitch.Thumb className={styles.thumb} />
        </BaseSwitch.Root>
        <span>{label}</span>
      </label>
    </Titled>
  );
}

type ChoiceFieldProps = {
  label: string;
  options: readonly string[];
  value: string;
  onChange: (value: string) => void;
};

export function ChoiceField({ label, options, value, onChange }: ChoiceFieldProps) {
  const id = useId();
  return (
    <div className={styles.field}>
      <span id={id} className={styles.label}>
        {label}
      </span>
      <RadioGroup
        className={styles.choices}
        aria-labelledby={id}
        value={value}
        onValueChange={(next) => {
          onChange(next);
        }}
      >
        {options.map((option) => (
          <Radio.Root key={option} value={option} className={styles.choice}>
            {option}
          </Radio.Root>
        ))}
      </RadioGroup>
    </div>
  );
}
