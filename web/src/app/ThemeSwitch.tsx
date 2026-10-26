import { Toggle } from "@base-ui/react/toggle";
import { ToggleGroup } from "@base-ui/react/toggle-group";
import type { ComponentType } from "react";
import { IconButton } from "../ui/Button";
import { type IconProps, Monitor, Moon, Sun } from "../ui/icons";
import styles from "./Layout.module.css";
import { THEMES, type Theme, useTheme } from "./theme";

const CHOICE: Record<Theme, { label: string; Icon: ComponentType<IconProps> }> = {
  light: { label: "Light", Icon: Sun },
  dark: { label: "Dark", Icon: Moon },
  system: { label: "Match my computer", Icon: Monitor },
};

function isTheme(value: string | undefined): value is Theme {
  return value !== undefined && value in CHOICE;
}

export function ThemeSwitch({ compact }: { compact: boolean }) {
  const theme = useTheme((state) => state.theme);
  const setTheme = useTheme((state) => state.setTheme);
  if (compact) {
    const next = THEMES[(THEMES.indexOf(theme) + 1) % THEMES.length] ?? "light";
    const { Icon } = CHOICE[theme];
    return (
      <IconButton
        label={`Theme: ${CHOICE[theme].label}. Switch to ${CHOICE[next].label}`}
        title={`Theme: ${CHOICE[theme].label}`}
        onClick={() => {
          setTheme(next);
        }}
      >
        <Icon size={14} />
      </IconButton>
    );
  }
  return (
    <ToggleGroup
      className={styles.themes}
      aria-label="Theme"
      value={[theme]}
      onValueChange={(value) => {
        const picked = value[0];
        if (isTheme(picked)) {
          setTheme(picked);
        }
      }}
    >
      {THEMES.map((item) => {
        const { label, Icon } = CHOICE[item];
        return (
          <Toggle key={item} value={item} className={styles.theme} aria-label={label} title={label}>
            <Icon size={13} />
          </Toggle>
        );
      })}
    </ToggleGroup>
  );
}
