import type { ReactNode, SVGProps } from "react";

export type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function Svg({ size = 16, children, ...props }: IconProps & { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 16 16"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      {children}
    </svg>
  );
}

function Pip({ cx, cy }: { cx: number; cy: number }) {
  return <circle cx={cx} cy={cy} r={1} fill="currentColor" stroke="none" />;
}

export function Home(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M2.5 7L8 2.5L13.5 7V12.5A1 1 0 0 1 12.5 13.5H3.5A1 1 0 0 1 2.5 12.5Z" />
      <path d="M6.5 13.5V10H9.5V13.5" />
    </Svg>
  );
}

export function Flow(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="4" cy="4" r="1.75" />
      <path d="M5.75 4H6.5A1.5 1.5 0 0 1 8 5.5V10.5A1.5 1.5 0 0 0 9.5 12H10.25" />
      <circle cx="12" cy="12" r="1.75" />
    </Svg>
  );
}

export function Rows(props: IconProps) {
  return (
    <Svg {...props}>
      <Pip cx={3} cy={4} />
      <Pip cx={3} cy={8} />
      <Pip cx={3} cy={12} />
      <path d="M6 4H13.5M6 8H13.5M6 12H13.5" />
    </Svg>
  );
}

export function Play(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M5.5 3.75V12.25L12 8Z" fill="currentColor" />
    </Svg>
  );
}

export function Spark(props: IconProps) {
  return (
    <Svg {...props}>
      <path
        d="M8 2C8.4 5.4 10.6 7.6 14 8C10.6 8.4 8.4 10.6 8 14C7.6 10.6 5.4 8.4 2 8C5.4 7.6 7.6 5.4 8 2Z"
        fill="currentColor"
        strokeWidth={1}
      />
    </Svg>
  );
}

export function Sliders(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M2.5 5H3.25M6.75 5H13.5" />
      <circle cx="5" cy="5" r="1.75" />
      <path d="M2.5 11H9.25M12.75 11H13.5" />
      <circle cx="11" cy="11" r="1.75" />
    </Svg>
  );
}

export function Check(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M3 8.5L6.5 12L13 4.5" />
    </Svg>
  );
}

export function Close(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M3.5 3.5L12.5 12.5M12.5 3.5L3.5 12.5" />
    </Svg>
  );
}

export function ChevronDown(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M4 6.25L8 10.25L12 6.25" />
    </Svg>
  );
}

export function ArrowRight(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M2.5 8H13" />
      <path d="M9 4L13 8L9 12" />
    </Svg>
  );
}

export function ArrowLeft(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M3 8H13.5" />
      <path d="M7 4L3 8L7 12" />
    </Svg>
  );
}

export function ArrowOut(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M4.5 11.5L11.5 4.5" />
      <path d="M6 4.5H11.5V10" />
    </Svg>
  );
}

export function Stop(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="4" y="4" width="8" height="8" rx="1.5" fill="currentColor" stroke="none" />
    </Svg>
  );
}

export function File(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M9 2H5A1.5 1.5 0 0 0 3.5 3.5V12.5A1.5 1.5 0 0 0 5 14H11A1.5 1.5 0 0 0 12.5 12.5V5.5Z" />
      <path d="M9 2V5.5H12.5" />
      <path d="M6 9H10M6 11.5H8.5" />
    </Svg>
  );
}

export function Image(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="2" y="2.5" width="12" height="11" rx="2" />
      <path d="M2.5 12L6.5 8L10 11.5M9 10.5L10.5 9L13.5 12" />
      <Pip cx={10.5} cy={5.75} />
    </Svg>
  );
}

export function Alert(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="8" cy="8" r="6" />
      <path d="M8 5V8.5" />
      <Pip cx={8} cy={10.75} />
    </Svg>
  );
}

export function Undo(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M6 2.5L2.5 6L6 9.5" />
      <path d="M3 6H10A3.5 3.5 0 0 1 10 13H6" />
    </Svg>
  );
}

export function Plus(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M8 3V13M3 8H13" />
    </Svg>
  );
}

export function Minus(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M3 8H13" />
    </Svg>
  );
}

export function Frame(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M2.5 6V4.5A2 2 0 0 1 4.5 2.5H6M10 2.5H11.5A2 2 0 0 1 13.5 4.5V6M13.5 10V11.5A2 2 0 0 1 11.5 13.5H10M6 13.5H4.5A2 2 0 0 1 2.5 11.5V10" />
    </Svg>
  );
}

export function Expand(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M9.5 2.5H13.5V6.5M13.5 2.5L9 7M6.5 13.5H2.5V9.5M2.5 13.5L7 9" />
    </Svg>
  );
}

export function Collapse(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M9.5 2.5V6.5H13.5M9.5 6.5L13.5 2.5M6.5 13.5V9.5H2.5M6.5 9.5L2.5 13.5" />
    </Svg>
  );
}

export function Sun(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="8" cy="8" r="2.75" />
      <path d="M8 1.75V2.75M8 13.25V14.25M1.75 8H2.75M13.25 8H14.25M3.6 3.6L4.3 4.3M11.7 11.7L12.4 12.4M3.6 12.4L4.3 11.7M11.7 4.3L12.4 3.6" />
    </Svg>
  );
}

export function Moon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M13.5 9.5A5.5 5.5 0 1 1 6.5 2.5A4.5 4.5 0 0 0 13.5 9.5Z" />
    </Svg>
  );
}

export function Monitor(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="2" y="2.5" width="12" height="8.5" rx="1.75" />
      <path d="M8 11V13.5M5.5 13.5H10.5" />
    </Svg>
  );
}

export function Pencil(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M10.5 2.75L13.25 5.5L6 12.75L2.75 13.25L3.25 10Z" />
      <path d="M9 4.25L11.75 7" />
    </Svg>
  );
}

export function Pointer(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M3.5 2.5L12.5 6.75L8.5 8.5L6.75 12.5Z" />
      <path d="M8.5 8.5L12 12" />
    </Svg>
  );
}

export function Clock(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="8" cy="8" r="6" />
      <path d="M8 5V8L10 9.5" />
    </Svg>
  );
}

export function Send(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M13.5 2.5L2.5 7L7 9L9 13.5Z" />
      <path d="M13.5 2.5L7 9" />
    </Svg>
  );
}

export function Inbox(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M2 9L3.75 3.75A1.5 1.5 0 0 1 5.2 2.75H10.8A1.5 1.5 0 0 1 12.25 3.75L14 9V12A1.5 1.5 0 0 1 12.5 13.5H3.5A1.5 1.5 0 0 1 2 12Z" />
      <path d="M2 9H5L6 10.5H10L11 9H14" />
    </Svg>
  );
}

export function Search(props: IconProps) {
  return (
    <Svg {...props}>
      <circle cx="7" cy="7" r="4.5" />
      <path d="M10.5 10.5L13.5 13.5" />
    </Svg>
  );
}

export function Filter(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M2.5 4H13.5M4.5 8H11.5M6.5 12H9.5" />
    </Svg>
  );
}

export function Copy(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="5.5" y="5.5" width="8" height="8" rx="1.75" />
      <path d="M10.5 3.25V3.25A1.25 1.25 0 0 0 9.25 2H3.25A1.25 1.25 0 0 0 2 3.25V9.25A1.25 1.25 0 0 0 3.25 10.5" />
    </Svg>
  );
}

export function Trash(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M2.5 4.5H13.5" />
      <path d="M6 4.5V3.25A1.25 1.25 0 0 1 7.25 2H8.75A1.25 1.25 0 0 1 10 3.25V4.5" />
      <path d="M3.75 4.5L4.4 12.85A1.25 1.25 0 0 0 5.65 14H10.35A1.25 1.25 0 0 0 11.6 12.85L12.25 4.5" />
    </Svg>
  );
}
