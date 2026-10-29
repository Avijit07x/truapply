import { useSuspenseQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { queries } from "../../api/queries";
import type { Extension, SettingsView } from "../../api/types";
import { CopyButton } from "../../components/CopyButton";
import { PageHeader, Row } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { Callout } from "../../ui/Callout";
import { Tabs } from "@base-ui/react/tabs";
import { navigate, useLocation } from "../../lib/router";
import { type TabItem, TabList } from "../../ui/Tabs";
import { toast } from "../../ui/toasts";
import { AutomaticRuns } from "./AutomaticRuns";
import { ResumeSection } from "./ResumeSection";
import {
  AboutYou,
  AutoSubmit,
  FormAnswers,
  Group,
  JobSearch,
  MoreFacts,
  PayAndNotice,
  PersonalDetails,
  ResumeChoice,
  RunsAndLimits,
  TimeFormat,
  type GroupProps,
  Wellfound,
  WorkPlaces,
  WorkRights,
} from "./SettingsGroups";
import styles from "./Settings.module.css";
import { useSettingsDraft } from "./useSettingsDraft";

function ExtensionSteps({ extension }: { extension: Extension }) {
  if (!extension.built) {
    return <Callout>Build it first: cd web && npm run build</Callout>;
  }
  return (
    <ol className={styles.steps}>
      <li>Open chrome://extensions in Chrome.</li>
      <li>Turn on Developer mode.</li>
      <li>
        Click Load unpacked and pick this folder:
        <span className={styles.folder}>
          <code>{extension.folder}</code>
          <CopyButton text={extension.folder} label="Copy the folder path" />
        </span>
      </li>
      <li>Keep the TruApply app running while you apply.</li>
    </ol>
  );
}

type ShownProps = GroupProps & { view: SettingsView };
type Tab = TabItem & { form: boolean; show: (props: ShownProps) => ReactNode };

const FIRST: Tab = {
  value: "profile",
  label: "Profile",
  form: true,
  show: (props) => (
    <>
      <AboutYou {...props} />
      <WorkRights {...props} />
      <PersonalDetails {...props} />
      <MoreFacts {...props} />
    </>
  ),
};
const TABS: readonly Tab[] = [
  FIRST,
  {
    value: "search",
    label: "Job search",
    form: true,
    show: (props) => (
      <>
        <JobSearch {...props} />
        <WorkPlaces {...props} />
        <PayAndNotice {...props} />
        <Wellfound {...props} />
      </>
    ),
  },
  {
    value: "applying",
    label: "Applying",
    form: true,
    show: (props) => (
      <>
        <FormAnswers {...props} />
        <ResumeChoice {...props} />
        <AutoSubmit {...props} />
        <RunsAndLimits {...props} />
      </>
    ),
  },
  {
    value: "automation",
    label: "Automation",
    form: true,
    show: ({ view, ...props }) => (
      <>
        <AutomaticRuns automatic={view.automatic} {...props} />
        <TimeFormat />
      </>
    ),
  },
  {
    value: "resume",
    label: "Resume and extension",
    form: false,
    show: ({ view }) => (
      <>
        <ResumeSection resume={view.resume} />
        <Group
          title="Chrome extension"
          note="Fills in applications in your own Chrome. You check each one and press Submit."
        >
          <ExtensionSteps extension={view.extension} />
        </Group>
      </>
    ),
  },
];

function useTab(): Tab {
  const { url } = useLocation();
  const wanted = url.searchParams.get("tab");
  return TABS.find((item) => item.value === wanted) ?? FIRST;
}

function SettingsForm({ view }: { view: SettingsView }) {
  const { group, dirty, saving, problems, submit, undo } = useSettingsDraft(view, () => {
    toast("Settings saved. They're used from the next run.");
  });
  const tab = useTab();
  return (
    <Tabs.Root
      value={tab.value}
      onValueChange={(value: string) => {
        navigate(`/settings?tab=${value}`, true);
      }}
      orientation="vertical"
      className={styles.tabs}
    >
      <TabList label="Settings" items={TABS} vertical />
      <form
        className={styles.form}
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <div className={styles.body}>
          <div className={styles.inner}>
            {tab.show({ ...group, view })}
            {problems.length > 0 && (
              <div className={styles.notice}>
                <Callout tone="bad">
                  <p>Nothing was saved. Fix these first:</p>
                  <ul className={styles.problems}>
                    {problems.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </Callout>
              </div>
            )}
          </div>
        </div>
        {(tab.form || dirty) && (
          <div className={styles.bar}>
            <span className={styles.state} role="status">
              {dirty ? "You have unsaved changes." : "Everything is saved."}
            </span>
            <Row>
              {dirty && (
                <Button variant="ghost" onClick={undo}>
                  Undo changes
                </Button>
              )}
              <Button type="submit" variant="primary" busy={saving} disabled={!dirty}>
                Save settings
              </Button>
            </Row>
          </div>
        )}
      </form>
    </Tabs.Root>
  );
}

export default function SettingsPage() {
  const { data } = useSuspenseQuery(queries.settings());
  return (
    <div className={styles.page}>
      <PageHeader
        title="Settings"
        description="Everything TruApply uses. Changes are used from the next run."
      />
      <SettingsForm view={data} />
    </div>
  );
}
