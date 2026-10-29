import { Tabs } from "@base-ui/react/tabs";
import { cx } from "../lib/cx";
import styles from "./Tabs.module.css";

export type TabItem = { value: string; label: string; count?: number };

type TabListProps = { items: readonly TabItem[]; label: string; vertical?: boolean };

export function TabList({ items, label, vertical = false }: TabListProps) {
  return (
    <Tabs.List className={cx(styles.list, vertical && styles.vertical)} aria-label={label}>
      {items.map((item) => (
        <Tabs.Tab key={item.value} value={item.value} className={styles.tab}>
          {item.label}
          {item.count !== undefined && (
            <span className={styles.tabCount}>{item.count.toLocaleString()}</span>
          )}
        </Tabs.Tab>
      ))}
      {!vertical && <Tabs.Indicator className={styles.indicator} />}
    </Tabs.List>
  );
}
