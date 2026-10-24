import type { ReactNode } from 'react'
import { Icon, type IconName } from './Icon'

export type Tone = 'sky' | 'indigo' | 'coral' | 'amber' | 'emerald'

/** KPI card. Must be rendered inside a <dl>. */
export function Stat({ label, icon, tone, children }: { label: string; icon: IconName; tone: Tone; children: ReactNode }) {
  return (
    <div className={`stat tone-${tone}`}>
      <span className="stat-icon">
        <Icon name={icon} size={20} />
      </span>
      <div>
        <dt>{label}</dt>
        <dd>{children}</dd>
      </div>
    </div>
  )
}
