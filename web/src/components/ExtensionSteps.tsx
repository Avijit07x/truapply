import type { Extension } from "../api/types";
import { useExtensionHere } from "../lib/extension";
import { Callout } from "../ui/Callout";
import { Check } from "../ui/icons";
import { Spinner } from "../ui/Spinner";
import { CopyButton } from "./CopyButton";
import styles from "./ExtensionSteps.module.css";

const EXTENSIONS_PAGE = "chrome://extensions";

export function ExtensionStatus() {
  const here = useExtensionHere();
  return here ? (
    <p className={styles.here} role="status">
      <Check size={14} />
      The extension is installed in this Chrome.
    </p>
  ) : (
    <p className={styles.waiting} role="status">
      <Spinner />
      Waiting for the extension. Open this page in the Chrome you added it to.
    </p>
  );
}

export function ExtensionSteps({ extension }: { extension: Extension }) {
  if (!extension.built) {
    return <Callout>Build it first: cd web && npm run build</Callout>;
  }
  return (
    <ol className={styles.steps}>
      <li>
        Open this page in Chrome:
        <span className={styles.folder}>
          <code>{EXTENSIONS_PAGE}</code>
          <CopyButton text={EXTENSIONS_PAGE} label="Copy the address" />
        </span>
      </li>
      <li>Turn on Developer mode, at the top right.</li>
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
