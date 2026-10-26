import { Toast } from "@base-ui/react/toast";

export type ToastTone = "info" | "error";

export const toastManager = Toast.createToastManager();

export function toast(text: string, tone: ToastTone = "info"): void {
  toastManager.add({ title: text, type: tone, priority: tone === "error" ? "high" : "low" });
}
