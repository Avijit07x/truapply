import type { ChangeEventHandler } from "react";
import styles from "./Jobs.module.css";

type TableCheckProps = {
  label: string;
  checked: boolean;
  indeterminate?: boolean;
  disabled?: boolean;
  title?: string;
  onChange: ChangeEventHandler<HTMLInputElement>;
};

export function TableCheck({ label, indeterminate = false, ...props }: TableCheckProps) {
  return (
    <input
      type="checkbox"
      className={styles.check}
      aria-label={label}
      ref={(node) => {
        if (node) {
          node.indeterminate = indeterminate;
        }
      }}
      {...props}
    />
  );
}
