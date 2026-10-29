import { RequestFailed } from "../../api/client";
import { useSetAutomatic } from "../../api/mutations";
import type { Automatic } from "../../api/types";
import { Callout } from "../../ui/Callout";
import { Switch } from "../../ui/Fields";
import { toast } from "../../ui/toasts";
import { type GroupProps, Group, fieldsFor } from "./SettingsGroups";
import styles from "./Settings.module.css";

const MINUTES_PER_HOUR = 60;

function every(minutes: number): string {
  const hours = Math.floor(minutes / MINUTES_PER_HOUR);
  const rest = minutes % MINUTES_PER_HOUR;
  return [hours ? `${String(hours)} h` : "", rest ? `${String(rest)} min` : ""]
    .filter(Boolean)
    .join(" ");
}

export function AutomaticRuns({ automatic, ...props }: GroupProps & { automatic: Automatic }) {
  const change = useSetAutomatic();
  const { number } = fieldsFor(props);
  const failed = change.error instanceof RequestFailed ? change.error.message : null;
  return (
    <Group
      title="Automatic runs"
      note="Finds, scores and gets jobs ready on its own while your Mac is awake. Nothing is ever sent."
    >
      {automatic.supported ? (
        <Switch
          label={
            automatic.on
              ? `On, every ${every(automatic.everyMinutes ?? 0)}`
              : "Off. It only runs when you press Run."
          }
          checked={automatic.on}
          onChange={(on) => {
            change.mutate(on, {
              onSuccess: () => {
                toast(on ? "Automatic runs are on." : "Automatic runs are off.");
              },
            });
          }}
        />
      ) : (
        <Callout>Automatic runs from this page work on macOS and Windows for now.</Callout>
      )}
      {automatic.elsewhere && (
        <Callout>
          Automatic runs are set up for another TruApply folder on this computer. Turning them on
          here moves them to this folder.
        </Callout>
      )}
      {failed && <Callout tone="bad">{failed}</Callout>}
      <div className={styles.pair}>
        {number("runEveryMinutes", "Minutes between runs", "15 to 1,440. 60 is every hour.")}
        {number("summaryHour", "Daily summary at", "Hour of the day, 0 to 23. 20 is 8 pm.")}
      </div>
    </Group>
  );
}
