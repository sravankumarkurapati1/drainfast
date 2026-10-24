// DrainFast brand mark: a water drop sitting on a storm-drain grate, inside a gradient tile.
import { useId } from 'react'

export function LogoMark({ size = 44 }: { size?: number }) {
  const id = useId().replace(/:/g, '')
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id={`bg-${id}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#22d3ee" />
          <stop offset="0.55" stopColor="#0ea5e9" />
          <stop offset="1" stopColor="#6366f1" />
        </linearGradient>
        <linearGradient id={`drop-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#ffffff" />
          <stop offset="1" stopColor="#e0f7ff" />
        </linearGradient>
      </defs>
      <rect x="2" y="2" width="60" height="60" rx="16" fill={`url(#bg-${id})`} />
      <path d="M32 9c7 8.5 12 15 12 21.5a12 12 0 0 1-24 0C20 24 25 17.5 32 9z" fill={`url(#drop-${id})`} />
      <path d="M27 27c-1.8 2.4-2.6 4.3-2.6 6" stroke="#0ea5e9" strokeWidth="2.4" strokeLinecap="round" fill="none" opacity="0.55" />
      <rect x="14" y="46" width="36" height="9" rx="3" fill="#0b1a33" opacity="0.9" />
      <path d="M20 47.5v6M26 47.5v6M32 47.5v6M38 47.5v6M44 47.5v6" stroke="#22d3ee" strokeWidth="2" strokeLinecap="round" />
    </svg>
  )
}

export function Wordmark() {
  return (
    <span className="wordmark">
      Drain<span className="wordmark-fast">Fast</span>
    </span>
  )
}
