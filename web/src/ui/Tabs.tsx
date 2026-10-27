import { Tabs } from "@base-ui/react/tabs";
import styles from "./Tabs.module.css";

export type TabItem = { value: string; label: string; count?: number };

export function TabList({ items, label }: { items: readonly TabItem[]; label: string }) {
  return (
    <Tabs.List className={styles.list} aria-label={label}>
      {items.map((item) => (
        <Tabs.Tab key={item.value} value={item.value} className={styles.tab}>
          {item.label}
          {item.count !== undefined && (
            <span className={styles.tabCount}>{item.count.toLocaleString()}</span>
          )}
        </Tabs.Tab>
      ))}
      <Tabs.Indicator className={styles.indicator} />
    </Tabs.List>
  );
}
