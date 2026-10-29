export function Logo({ size = 22 }: { size?: number }) {
  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      aria-hidden="true"
      focusable="false"
      fill="none"
      stroke="var(--accent)"
      strokeWidth={7}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M8 36L21 49L47 23" />
      <path d="M32 21H49V38" />
    </svg>
  );
}
