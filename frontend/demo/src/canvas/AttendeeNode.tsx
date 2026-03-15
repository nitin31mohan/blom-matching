import type { SimNode } from '../types'

interface Props {
  node: SimNode
  color: string       // fit fill color (green/amber/red)
  groupColor: string  // identity stroke color (purple/sky/etc)
  onDragStart: (e: React.PointerEvent, node: SimNode) => void
  isFrozen: boolean
  isApproved?: boolean
  isStraggler?: boolean
}

export default function AttendeeNode({ node, color, groupColor, onDragStart, isFrozen, isApproved, isStraggler }: Props) {
  const isLocked = isFrozen && isApproved && !isStraggler
  return (
    <g
      transform={`translate(${node.x},${node.y})`}
      onPointerDown={(e) => onDragStart(e, node)}
    >
      {/* Expanded touch hit area — 44px diameter (r=22) */}
      <circle r={22} fill="transparent" style={{ cursor: isLocked ? 'default' : 'grab' }} />
      {/* Straggler: yellow outward-wave pulse — takes precedence over approved ring */}
      {isStraggler && (
        <>
          <circle cx={0} cy={0} r={20} fill="none" stroke="#facc15" strokeWidth={2}>
            <animate attributeName="r" from="20" to="36" dur="1.5s" repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.8;0" dur="1.5s" repeatCount="indefinite" />
          </circle>
          <circle cx={0} cy={0} r={20} fill="none" stroke="#facc15" strokeWidth={1.5}>
            <animate attributeName="r" from="20" to="36" dur="1.5s" begin="0.6s" repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.5;0" dur="1.5s" begin="0.6s" repeatCount="indefinite" />
          </circle>
        </>
      )}
      {/* Approved + frozen: lock icon badge at bottom-right */}
      {!isStraggler && isApproved && isFrozen && (
        <g transform="translate(8, 8)" style={{ pointerEvents: 'none' }}>
          <circle cx={4} cy={5.5} r={6} fill="#0f172a" />
          <path d="M1.5 5 V3.2 a2.5 2.5 0 0 1 5 0 V5" fill="none" stroke="#22c55e" strokeWidth={1.3} strokeLinecap="round" />
          <rect x={0.5} y={4.5} width={7} height={5.5} rx={1} fill="#22c55e" />
          <circle cx={4} cy={7.2} r={1} fill="#0f172a" />
        </g>
      )}
      <circle r={18} fill={color} fillOpacity={0.85} stroke={groupColor} strokeWidth={2.5} />
      <text
        textAnchor="middle"
        dy="0.35em"
        fontSize={11}
        fontWeight={600}
        fill="#fff"
        style={{ userSelect: 'none', pointerEvents: 'none' }}
      >
        {node.display_name[0]}
      </text>
      <text
        textAnchor="middle"
        y={26}
        fontSize={9}
        fill="#94a3b8"
        style={{ userSelect: 'none', pointerEvents: 'none' }}
      >
        {node.display_name.split(' ')[0]}
      </text>
    </g>
  )
}
