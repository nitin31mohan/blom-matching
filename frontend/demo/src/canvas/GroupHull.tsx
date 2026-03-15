import React from 'react'
import { polygonHull } from 'd3-polygon'
import type { SimNode, FitBreakdown } from '../types'
import { fitColor } from '../lib/fit'

interface Props {
  nodes: SimNode[]
  color: string         // identity color from GROUP_LAYOUT
  label: string
  fitBreakdown?: FitBreakdown
  viewMode: 'simple' | 'detailed'
  overCapacity?: number
  onDragHandlePointerDown?: (e: React.PointerEvent) => void
}

function FitLabel({
  cx,
  labelY,
  fitBreakdown,
  viewMode,
}: {
  cx: number
  labelY: number
  fitBreakdown: FitBreakdown
  viewMode: 'simple' | 'detailed'
}) {
  if (viewMode === 'simple') {
    return (
      <text
        x={cx}
        y={labelY + 15}
        textAnchor="middle"
        fontSize={11}
        fontFamily="system-ui, sans-serif"
        fontWeight={500}
        fill={fitColor(fitBreakdown.composite)}
        style={{ userSelect: 'none', pointerEvents: 'none' }}
      >
        {Math.round(fitBreakdown.composite * 100)}% fit
      </text>
    )
  }

  return (
    <>
      <text
        x={cx - 18}
        y={labelY + 15}
        textAnchor="middle"
        fontSize={10}
        fontFamily="system-ui, sans-serif"
        fontWeight={500}
        fill={fitColor(fitBreakdown.valuesCohesion)}
        style={{ userSelect: 'none', pointerEvents: 'none' }}
      >
        V:{Math.round(fitBreakdown.valuesCohesion * 100)}
      </text>
      <text
        x={cx + 18}
        y={labelY + 15}
        textAnchor="middle"
        fontSize={10}
        fontFamily="system-ui, sans-serif"
        fontWeight={500}
        fill={fitColor(fitBreakdown.dominanceBalance)}
        style={{ userSelect: 'none', pointerEvents: 'none' }}
      >
        D:{Math.round(fitBreakdown.dominanceBalance * 100)}
      </text>
    </>
  )
}

function DragHandle({ x, y, onPointerDown }: { x: number; y: number; onPointerDown: (e: React.PointerEvent) => void }) {
  return (
    <g
      transform={`translate(${x}, ${y})`}
      onPointerDown={onPointerDown}
      style={{ cursor: 'grab', pointerEvents: 'all' }}
    >
      {/* Expanded touch hit area */}
      <rect x={-10} y={-10} width={20} height={20} fill="transparent" />
      {/* Three-line grip icon */}
      {([-3, 0, 3] as number[]).map(dy => (
        <line key={dy} x1={-5} y1={dy} x2={5} y2={dy} stroke="#64748b" strokeWidth={1.3} strokeLinecap="round" />
      ))}
    </g>
  )
}

export default function GroupHull({ nodes, color, label, fitBreakdown, viewMode, overCapacity, onDragHandlePointerDown }: Props) {
  if (nodes.length === 0) return null

  const cx = nodes.reduce((s, n) => s + n.x, 0) / nodes.length
  const cy = nodes.reduce((s, n) => s + n.y, 0) / nodes.length
  const PAD = 28

  // 8-point circle expansion per node — better hull shape for close clusters
  const padded: [number, number][] = []
  nodes.forEach((n) => {
    for (let a = 0; a < 8; a++) {
      padded.push([
        n.x + PAD * Math.cos((a * Math.PI) / 4),
        n.y + PAD * Math.sin((a * Math.PI) / 4),
      ])
    }
  })

  if (padded.length < 3) {
    return (
      <>
        <circle
          cx={cx}
          cy={cy}
          r={PAD + 22}
          fill={color}
          fillOpacity={0.12}
          stroke={color}
          strokeWidth={1.5}
          strokeDasharray="5 3"
        />
        <text
          x={cx}
          y={cy - PAD - 28}
          textAnchor="middle"
          fontSize={12}
          fontFamily="system-ui, sans-serif"
          fontWeight={600}
          fill={color}
          fillOpacity={0.8}
          style={{ userSelect: 'none', pointerEvents: 'none' }}
        >
          {label}
        </text>
        {fitBreakdown && (
          <FitLabel
            cx={cx}
            labelY={cy - PAD - 28}
            fitBreakdown={fitBreakdown}
            viewMode={viewMode}
          />
        )}
        {overCapacity !== undefined && overCapacity > 0 && (
          <text
            x={cx}
            y={cy - PAD - 42}
            textAnchor="middle"
            fontSize={10}
            fontFamily="system-ui, sans-serif"
            fontWeight={500}
            fill="#f59e0b"
            style={{ userSelect: 'none', pointerEvents: 'none' }}
          >
            +{overCapacity} over capacity
          </text>
        )}
        {onDragHandlePointerDown && (
          <DragHandle x={cx + PAD + 16} y={cy - PAD - 28} onPointerDown={onDragHandlePointerDown} />
        )}
      </>
    )
  }

  const hull = polygonHull(padded)
  if (!hull) return null

  const d = `M${hull.map((p) => p.join(',')).join('L')}Z`
  const labelY = Math.min(...hull.map((p) => p[1])) - 10

  return (
    <>
      <path
        d={d}
        fill={color}
        fillOpacity={0.12}
        stroke={color}
        strokeWidth={1.5}
        strokeDasharray="5 3"
      />
      <text
        x={cx}
        y={labelY}
        textAnchor="middle"
        fontSize={12}
        fontFamily="system-ui, sans-serif"
        fontWeight={600}
        fill={color}
        fillOpacity={0.8}
        style={{ userSelect: 'none', pointerEvents: 'none' }}
      >
        {label}
      </text>
      {fitBreakdown && (
        <FitLabel
          cx={cx}
          labelY={labelY}
          fitBreakdown={fitBreakdown}
          viewMode={viewMode}
        />
      )}
      {overCapacity !== undefined && overCapacity > 0 && (
        <text
          x={cx}
          y={labelY - 12}
          textAnchor="middle"
          fontSize={10}
          fontFamily="system-ui, sans-serif"
          fontWeight={500}
          fill="#f59e0b"
          style={{ userSelect: 'none', pointerEvents: 'none' }}
        >
          +{overCapacity} over capacity
        </text>
      )}
      {onDragHandlePointerDown && (
        <DragHandle x={cx + 36} y={labelY - 2} onPointerDown={onDragHandlePointerDown} />
      )}
    </>
  )
}
