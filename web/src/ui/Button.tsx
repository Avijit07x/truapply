import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cx } from "../lib/cx";
import { Link } from "../lib/router";
import styles from "./Button.module.css";

type Variant = "primary" | "secondary" | "ghost" | "danger";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  busy?: boolean;
  icon?: ReactNode;
};

export function Button({
  variant = "secondary",
  busy = false,
  icon,
  type = "button",
  disabled,
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={cx(styles.button, styles[variant], className)}
      disabled={Boolean(disabled) || busy}
      aria-busy={busy || undefined}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}

type ButtonLinkProps = { to: string; variant?: Variant; icon?: ReactNode; children: ReactNode };

export function ButtonLink({ to, variant = "secondary", icon, children }: ButtonLinkProps) {
  return (
    <Link to={to} className={cx(styles.button, styles[variant])}>
      {icon}
      {children}
    </Link>
  );
}

export function IconButton({
  label,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { label: string }) {
  return (
    <button type="button" className={styles.iconButton} aria-label={label} {...props}>
      {children}
    </button>
  );
}
