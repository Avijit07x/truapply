import { useRef } from "react";
import { RequestFailed } from "../../api/client";
import { useReplaceResume } from "../../api/mutations";
import type { ResumeInfo } from "../../api/types";
import { Note, Row, Stack } from "../../ui/Blocks";
import { Button } from "../../ui/Button";
import { Callout } from "../../ui/Callout";
import { toast } from "../../ui/toasts";
import { Group } from "./SettingsGroups";

const KINDS = ".tex,.pdf,.docx,.md,.txt";
const FORMATS = {
  latex: "Your own LaTeX design",
  structured: "The built-in one-column design",
} as const;

function base64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = typeof reader.result === "string" ? reader.result : "";
      resolve(result.split(",")[1] ?? "");
    };
    reader.onerror = () => {
      reject(reader.error ?? new Error("The file couldn't be read."));
    };
    reader.readAsDataURL(file);
  });
}

export function ResumeSection({ resume }: { resume: ResumeInfo }) {
  const picker = useRef<HTMLInputElement>(null);
  const replace = useReplaceResume();
  const failed = replace.error instanceof RequestFailed ? replace.error.message : null;
  const send = async (file: File) => {
    const data = await base64(file);
    replace.mutate(
      { name: file.name, data },
      {
        onSuccess: ({ pages }) => {
          toast(`Resume replaced. ${String(pages)} page${pages === 1 ? "" : "s"}.`);
        },
      },
    );
  };
  return (
    <Group
      title="Resume"
      note="Your master resume. Every tailored resume starts from it and uses only its facts."
    >
      <Stack>
        <p>Now using: {FORMATS[resume.format]}</p>
        <input
          ref={picker}
          type="file"
          accept={KINDS}
          hidden
          aria-label="Resume file"
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            if (file) void send(file);
          }}
        />
        <Row>
          <Button
            variant="secondary"
            busy={replace.isPending}
            onClick={() => picker.current?.click()}
          >
            Replace resume
          </Button>
        </Row>
        <Note>
          {replace.isPending
            ? "Reading your resume. A PDF or Word file goes to Claude, which can take a minute."
            : "A .tex file keeps your design. PDF, Word, Markdown or text move into the built-in design. Your other settings stay as they are."}
        </Note>
        {failed && <Callout tone="bad">{failed}</Callout>}
      </Stack>
    </Group>
  );
}
