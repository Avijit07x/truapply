import { Popover } from "@base-ui/react/popover";
import { type ReactNode, useState } from "react";
import { navigate } from "../../lib/router";
import { ChevronDown } from "../../ui/icons";
import styles from "./Jobs.module.css";

export type MenuChoice = { key: string; label: string; count: number; to: string };

type ChipMenuProps = {
  label: string;
  title: string;
  choices: readonly MenuChoice[];
  picked: string | null;
  anyTo: string;
  any?: string;
  idle?: string;
  icon?: ReactNode;
};

function Choice({
  on,
  children,
  onPick,
}: {
  on: boolean;
  children: ReactNode;
  onPick: () => void;
}) {
  return (
    <button type="button" className={styles.choice} aria-pressed={on} onClick={onPick}>
      {children}
    </button>
  );
}

export function ChipMenu({
  label,
  title,
  choices,
  picked,
  anyTo,
  any = "Any",
  idle = `${label}: any`,
  icon,
}: ChipMenuProps) {
  const [open, setOpen] = useState(false);
  const chosen = choices.find((choice) => choice.key === picked);
  const go = (to: string) => () => {
    navigate(to);
    setOpen(false);
  };
  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger className={styles.menuButton} aria-current={chosen ? "true" : undefined}>
        {icon}
        {chosen ? `${label}: ${chosen.label}` : idle}
        <ChevronDown size={10} />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Positioner className={styles.positioner} sideOffset={6} align="start">
          <Popover.Popup className={styles.popup}>
            <Popover.Title className={styles.popupTitle}>{title}</Popover.Title>
            <div className={styles.statusChoices} role="group" aria-label={title}>
              <Choice on={!chosen} onPick={go(anyTo)}>
                {any}
              </Choice>
              {choices.map((choice) => (
                <Choice key={choice.key} on={choice === chosen} onPick={go(choice.to)}>
                  {choice.label}
                  <span className={styles.choiceCount}>{choice.count.toLocaleString()}</span>
                </Choice>
              ))}
            </div>
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}
