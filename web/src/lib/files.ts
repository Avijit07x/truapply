export const RESUME_KINDS = ".tex,.pdf,.docx,.md,.txt";

export function base64(file: File): Promise<string> {
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
