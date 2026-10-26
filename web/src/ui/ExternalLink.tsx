import type { ReactNode } from "react";
import { cx } from "../lib/cx";
import buttonStyles from "./Button.module.css";
import { ArrowOut } from "./icons";

type ExternalLinkProps = { href: string; children: ReactNode; asButton?: boolean };

export function ExternalLink({ href, children, asButton = false }: ExternalLinkProps) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={asButton ? cx(buttonStyles.button, buttonStyles.secondary) : undefined}
    >
      {children}
      <ArrowOut size={12} />
    </a>
  );
}
