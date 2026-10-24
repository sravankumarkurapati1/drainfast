// Small inline stroke icons (no icon library dependency). Decorative: callers keep them aria-hidden.
export type IconName =
  | 'drop'
  | 'list'
  | 'map'
  | 'inbox'
  | 'chart'
  | 'rain'
  | 'tide'
  | 'crew'
  | 'pin'
  | 'alert'
  | 'clock'
  | 'target'
  | 'wrench'
  | 'sun'

const PATHS: Record<IconName, string> = {
  drop: 'M12 2.7c3.6 4.3 6 7.7 6 10.8a6 6 0 0 1-12 0c0-3.1 2.4-6.5 6-10.8z',
  list: 'M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01',
  map: 'M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2zM9 4v14M15 6v14',
  inbox: 'M3 13h5l2 3h4l2-3h5M5 5h14l2 8v6H3v-6l2-8z',
  chart: 'M4 20V10M10 20V4M16 20v-7M22 20H2',
  rain: 'M17.5 15a4.5 4.5 0 0 0-1-8.9A6 6 0 0 0 5 8a4 4 0 0 0 .5 8M8 19l1-2M12 21l1-3M16 19l1-2',
  tide: 'M2 12c2 0 2-2 4-2s2 2 4 2 2-2 4-2 2 2 4 2 2-2 4-2M2 18c2 0 2-2 4-2s2 2 4 2 2-2 4-2 2 2 4 2 2-2 4-2M12 3v4M9 5l3 2 3-2',
  crew: 'M16 20v-1.5a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 4 18.5V20M10 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM20 20v-1.5a3.5 3.5 0 0 0-2.5-3.4M15.5 4.2a3.5 3.5 0 0 1 0 6.6',
  pin: 'M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21zM12 12a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5z',
  alert: 'M12 3 2 20h20L12 3zM12 10v4M12 17h.01',
  clock: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 7v5l3 2',
  target: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM12 12h.01',
  sun: 'M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4',
  wrench: 'M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4 2.5-2.5z',
}

export function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d={PATHS[name]} />
    </svg>
  )
}
