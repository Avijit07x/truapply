import { IconButton } from "../ui/Button";
import { Copy } from "../ui/icons";
import { toast } from "../ui/toasts";

export function copyText(text: string, done = "Copied."): void {
  navigator.clipboard.writeText(text).then(
    () => {
      toast(done);
    },
    () => {
      toast("Couldn't copy. Select the text and copy it instead.");
    },
  );
}

export function CopyButton({ text, label }: { text: string; label: string }) {
  return (
    <IconButton
      label={label}
      title={label}
      onClick={() => {
        copyText(text);
      }}
    >
      <Copy size={14} />
    </IconButton>
  );
}
