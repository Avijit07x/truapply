import { Toast } from "@base-ui/react/toast";
import { IconButton } from "./Button";
import styles from "./Toaster.module.css";
import { Close } from "./icons";
import { toastManager } from "./toasts";

const SHOWN_FOR_MS = 4_000;
const MAX_SHOWN = 3;

function ToastList() {
  const { toasts } = Toast.useToastManager();
  return toasts.map((item) => (
    <Toast.Root key={item.id} toast={item} className={styles.toast}>
      <Toast.Content className={styles.content}>
        <Toast.Title className={styles.title} />
        <Toast.Close render={<IconButton label="Close" />}>
          <Close size={12} />
        </Toast.Close>
      </Toast.Content>
    </Toast.Root>
  ));
}

export function Toaster() {
  return (
    <Toast.Provider toastManager={toastManager} timeout={SHOWN_FOR_MS} limit={MAX_SHOWN}>
      <Toast.Portal>
        <Toast.Viewport className={styles.viewport}>
          <ToastList />
        </Toast.Viewport>
      </Toast.Portal>
    </Toast.Provider>
  );
}
