import { useEffect, useRef, useState } from "react";
import { cx } from "../lib/cx";
import { Search } from "./icons";
import styles from "./SearchBox.module.css";

const WAIT_MS = 250;
const LONGEST = 100;

type SearchBoxProps = {
  value: string;
  onSearch: (value: string) => void;
  label?: string;
  placeholder?: string;
  autoFocus?: boolean;
  wide?: boolean;
};

export function SearchBox({
  value,
  onSearch,
  label = "Search jobs",
  placeholder = "Search title or company",
  autoFocus = false,
  wide = false,
}: SearchBoxProps) {
  const [text, setText] = useState(value);
  const [sent, setSent] = useState(value);
  const timer = useRef(0);
  if (value !== sent) {
    setSent(value);
    setText(value);
  }
  useEffect(() => {
    const pending = timer;
    return () => {
      window.clearTimeout(pending.current);
    };
  }, []);
  return (
    <label className={cx(styles.search, wide && styles.wide)}>
      <Search size={14} />
      <input
        type="search"
        placeholder={placeholder}
        aria-label={label}
        autoFocus={autoFocus}
        maxLength={LONGEST}
        value={text}
        onChange={(event) => {
          const next = event.target.value;
          setText(next);
          window.clearTimeout(timer.current);
          timer.current = window.setTimeout(() => {
            setSent(next.trim());
            onSearch(next.trim());
          }, WAIT_MS);
        }}
      />
    </label>
  );
}
