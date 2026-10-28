import { useId } from "react";

export function Logo({ size = 22 }: { size?: number }) {
  const id = useId();
  return (
    <svg viewBox="0 0 64 64" width={size} height={size} aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id={`${id}fill`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#3f3f46" />
          <stop offset="1" stopColor="#09090b" />
        </linearGradient>
        <linearGradient id={`${id}sheen`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#fff" stopOpacity={0.22} />
          <stop offset="0.5" stopColor="#fff" stopOpacity={0} />
        </linearGradient>
        <filter id={`${id}shadow`} x="-20%" y="-20%" width="140%" height="160%">
          <feDropShadow dx="0" dy="1.5" stdDeviation="1.5" floodColor="#000" floodOpacity={0.35} />
        </filter>
      </defs>
      <rect width="64" height="64" rx="15" fill={`url(#${id}fill)`} />
      <rect width="64" height="64" rx="15" fill={`url(#${id}sheen)`} />
      <rect
        x="0.75"
        y="0.75"
        width="62.5"
        height="62.5"
        rx="14.25"
        fill="none"
        stroke="#fff"
        strokeOpacity={0.12}
        strokeWidth={1.5}
      />
      <g fill="none" stroke="#fff" strokeWidth={6} filter={`url(#${id}shadow)`}>
        <path d="M15 34L25 44L45 24" />
        <path d="M33 22.5H46.5V36" />
      </g>
    </svg>
  );
}
