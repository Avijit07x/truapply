const NON_WORD = /[^\p{L}\p{N}]+/gu;

export const normalize = (text: string) =>
  text.toLowerCase().replace(NON_WORD, " ").trim().replace(/\s+/g, " ");

export function bestOption(options: string[], answer: string): number | null {
  const wanted = normalize(answer);
  if (!wanted) return null;
  const names = options.map(normalize);
  const words = wanted.split(" ");
  const tests = [
    (name: string) => name === wanted,
    (name: string) => name.startsWith(`${wanted} `) || wanted.startsWith(`${name} `),
    (name: string) => ` ${name} `.includes(` ${wanted} `),
    (name: string) => words.every((word) => name.split(" ").includes(word)),
  ];
  for (const test of tests) {
    const index = names.findIndex((name) => name !== "" && test(name));
    if (index >= 0) return index;
  }
  return null;
}
