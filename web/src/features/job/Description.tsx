import { Collapsible } from "@base-ui/react/collapsible";
import { ChevronDown } from "../../ui/icons";
import styles from "./Job.module.css";

export function Description({ text, open = false }: { text: string; open?: boolean }) {
  return (
    <Collapsible.Root className={styles.description} defaultOpen={open}>
      <Collapsible.Trigger className={styles.descriptionToggle}>
        <ChevronDown size={12} className={styles.chevron} />
        Job description
      </Collapsible.Trigger>
      <Collapsible.Panel className={styles.descriptionPanel}>
        <p className={styles.descriptionText}>{text}</p>
      </Collapsible.Panel>
    </Collapsible.Root>
  );
}
