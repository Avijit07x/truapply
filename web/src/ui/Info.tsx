import { Popover } from "@base-ui/react/popover";
import type { ReactNode } from "react";
import buttonStyles from "./Button.module.css";
import { Info as InfoIcon } from "./icons";
import styles from "./Info.module.css";

export function Info({ about, children }: { about: string; children: ReactNode }) {
  return (
    <Popover.Root>
      <Popover.Trigger
        type="button"
        className={buttonStyles.iconButton}
        aria-label={about ? `About ${about}` : "About this setting"}
      >
        <InfoIcon size={14} />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Positioner className={styles.positioner} sideOffset={6} align="start">
          <Popover.Popup className={styles.popup}>{children}</Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  );
}
