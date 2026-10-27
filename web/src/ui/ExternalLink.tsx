import type { ReactNode } from "react";
import { cx } from "../lib/cx";
import buttonStyles from "./Button.module.css";
import { ArrowOut } from "./icons";

type ExternalLinkProps = {
  href: string;
  children: ReactNode;
  button?: "primary" | "secondary";
};

export function ExternalLink({ href, children, button }: ExternalLinkProps) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className={button && cx(buttonStyles.button, buttonStyles[button])}
    >
      {children}
      <ArrowOut size={12} />
    </a>
  );
}
