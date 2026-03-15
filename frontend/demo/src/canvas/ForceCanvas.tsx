import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import * as d3 from 'd3'
import type { GroupAssignment, Attendee, SimNode, ActivityProfile, PairScoreMap, FitBreakdown, GroupLayout } from '../types'
import { fitScore, fitScoreDetailed, fitColor } from '../lib/fit'
import AttendeeNode from './AttendeeNode'
import GroupHull from './GroupHull'
interface Props {
  assignment: GroupAssignment
  attendees: Attendee[]
  layout: GroupLayout[]
  width: number
  height: number
  onNodeClick?: (node: SimNode) => void
  onClearSelection?: () => void
  onReassign?: (userId: string, newGroupId: string) => void
  activeProfile: ActivityProfile
  pairScores?: PairScoreMap
  viewMode: 'simple' | 'detailed'
  isFrozen: boolean
  groupSizeLimit?: number
  onDeleteGroup?: (groupId: string) => void
}

function buildSimNodes(attendees: Attendee[], width: number, height: number): SimNode[] {
  return attendees.map((a) => ({
    ...a,
    x: width / 2 + (Math.random() - 0.5) * 200,
    y: height / 2 + (Math.random() - 0.5) * 200,
    vx: 0,
    vy: 0,
    fx: null,
    fy: null,
  }))
}

export default function ForceCanvas({
  assignment,
  attendees,
  layout,
  width,
  height,
  onNodeClick,
  onClearSelection,
  onReassign,
  activeProfile,
  pairScores = {},
  viewMode,
  isFrozen,
  groupSizeLimit,
  onDeleteGroup,
}: Props) {
  const nodesRef = useRef<SimNode[]>(buildSimNodes(attendees, width, height))
  const simRef = useRef<d3.Simulation<SimNode, undefined> | null>(null)
  const svgRef = useRef<SVGSVGElement | null>(null)
  const [, setTick] = useState(0)
  const [draggingGroupId, setDraggingGroupId] = useState<string | null>(null)
  const [hullDragPos, setHullDragPos] = useState<{ x: number; y: number } | null>(null)

  const groupCenter = useCallback(
    (groupId: string): [number, number] => {
      const gl = layout.find((l) => l.group_id === groupId)
      return gl ? [gl.cx * width, gl.cy * height] : [width / 2, height / 2]
    },
    [layout, width, height]
  )

  const groupIdentityColor = useCallback(
    (groupId: string): string =>
      layout.find((l) => l.group_id === groupId)?.color ?? '#94a3b8',
    [layout]
  )

  // Sync nodesRef when attendees list changes (e.g., after reassignment from panel)
  useEffect(() => {
    const nodes = nodesRef.current
    for (const a of attendees) {
      const node = nodes.find((n) => n.pipeline_user_id === a.pipeline_user_id)
      if (node && node.group_id !== a.group_id) {
        node.group_id = a.group_id
      }
    }
    // Update forceX/Y to react to new group assignments
    const sim = simRef.current
    if (sim) {
      sim
        .force('groupX', d3.forceX<SimNode>((d) => groupCenter(d.group_id)[0]).strength(0.18))
        .force('groupY', d3.forceY<SimNode>((d) => groupCenter(d.group_id)[1]).strength(0.18))
      sim.alpha(0.4).restart()
    }
  }, [attendees, groupCenter])

  useEffect(() => {
    const nodes = nodesRef.current

    const sim = d3
      .forceSimulation<SimNode>(nodes)
      .force('groupX', d3.forceX<SimNode>((d) => groupCenter(d.group_id)[0]).strength(0.18))
      .force('groupY', d3.forceY<SimNode>((d) => groupCenter(d.group_id)[1]).strength(0.18))
      .force('charge', d3.forceManyBody<SimNode>().strength(-40))
      .force('collide', d3.forceCollide<SimNode>(26))
      .alphaDecay(0.02)
      .on('tick', () => {
        nodes.forEach((d) => {
          d.x = Math.max(22, Math.min(width - 22, d.x ?? width / 2))
          d.y = Math.max(22, Math.min(height - 36, d.y ?? height / 2))
        })
        setTick((t) => t + 1)
      })

    simRef.current = sim

    return () => {
      sim.stop()
    }
  }, [assignment, width, height]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleDragStart = useCallback(
    (e: React.PointerEvent, node: SimNode) => {
      e.preventDefault()
      const svgEl = svgRef.current!

      // Locked nodes: click to select only, no drag or reassignment
      if (isFrozen && node.isApproved && !node.isStraggler) {
        let moved = false
        const onMove = () => { moved = true }
        const onUp = () => {
          window.removeEventListener('pointermove', onMove)
          window.removeEventListener('pointerup', onUp)
          if (!moved) onNodeClick?.(node)
        }
        window.addEventListener('pointermove', onMove)
        window.addEventListener('pointerup', onUp)
        return
      }

      simRef.current?.alphaTarget(0.3).restart()

      let hasMoved = false
      let lastClientX = e.clientX
      let lastClientY = e.clientY
      let velX = 0
      let velY = 0

      const getPos = (ev: PointerEvent) => {
        const r = svgEl.getBoundingClientRect()
        return { x: ev.clientX - r.left, y: ev.clientY - r.top }
      }

      const onMove = (ev: PointerEvent) => {
        hasMoved = true
        velX = ev.clientX - lastClientX
        velY = ev.clientY - lastClientY
        lastClientX = ev.clientX
        lastClientY = ev.clientY
        const p = getPos(ev)
        node.fx = p.x
        node.fy = p.y
      }

      const onUp = (ev: PointerEvent) => {
        window.removeEventListener('pointermove', onMove)
        window.removeEventListener('pointerup', onUp)

        if (!hasMoved) {
          // Click/tap — open detail panel
          node.fx = null
          node.fy = null
          simRef.current?.alphaTarget(0)
          onNodeClick?.(node)
          return
        }

        const pos = getPos(ev)

        // Check for reassignment: nearest group center within 110px
        let nearest = node.group_id
        let nearestDist = Infinity
        for (const gl of layout) {
          const [cx, cy] = groupCenter(gl.group_id)
          const dist = Math.hypot(pos.x - cx, pos.y - cy)
          if (dist < nearestDist) {
            nearestDist = dist
            nearest = gl.group_id
          }
        }
        if (nearestDist < 110 && nearest !== node.group_id) {
          node.group_id = nearest
          onReassign?.(node.pipeline_user_id, nearest)
          simRef.current
            ?.force('groupX', d3.forceX<SimNode>((d) => groupCenter(d.group_id)[0]).strength(0.18))
            .force('groupY', d3.forceY<SimNode>((d) => groupCenter(d.group_id)[1]).strength(0.18))
          simRef.current?.alpha(0.4).restart()
        }

        // Throw physics
        node.fx = null
        node.fy = null
        const speed = Math.sqrt(velX * velX + velY * velY)
        if (speed > 3) {
          node.vx = velX * 5
          node.vy = velY * 5
          simRef.current?.alpha(0.5).restart()
        } else {
          simRef.current?.alphaTarget(0)
        }
      }

      window.addEventListener('pointermove', onMove)
      window.addEventListener('pointerup', onUp)
    },
    [layout, groupCenter, onNodeClick, onReassign, isFrozen]
  )

  const makeHullDragHandler = useCallback(
    (groupId: string) => (e: React.PointerEvent) => {
      e.preventDefault()
      e.stopPropagation()
      const svgEl = svgRef.current!
      setDraggingGroupId(groupId)

      const getPos = (ev: PointerEvent) => {
        const r = svgEl.getBoundingClientRect()
        return { x: ev.clientX - r.left, y: ev.clientY - r.top }
      }

      const onMove = (ev: PointerEvent) => setHullDragPos(getPos(ev))

      const onUp = (ev: PointerEvent) => {
        window.removeEventListener('pointermove', onMove)
        window.removeEventListener('pointerup', onUp)
        const pos = getPos(ev)
        // Dustbin zone: bottom-right 76×76 px area
        if (pos.x > width - 76 && pos.y > height - 76) {
          onDeleteGroup?.(groupId)
        }
        setDraggingGroupId(null)
        setHullDragPos(null)
      }

      window.addEventListener('pointermove', onMove)
      window.addEventListener('pointerup', onUp)
    },
    [width, height, onDeleteGroup]
  )

  const isOverDustbin = useMemo(
    () => hullDragPos !== null && hullDragPos.x > width - 76 && hullDragPos.y > height - 76,
    [hullDragPos, width, height]
  )

  const nodes = nodesRef.current

  // Group nodes by group_id for hull rendering
  const nodesByGroup: Record<string, SimNode[]> = {}
  for (const node of nodes) {
    if (!nodesByGroup[node.group_id]) nodesByGroup[node.group_id] = []
    nodesByGroup[node.group_id].push(node)
  }

  // Group-level fit: average breakdown of all members
  const groupFitBreakdown: Record<string, FitBreakdown> = {}
  for (const [gid, gnodes] of Object.entries(nodesByGroup)) {
    const breakdowns = gnodes.map((n) =>
      fitScoreDetailed(n, gid, nodes, activeProfile, pairScores)
    )
    groupFitBreakdown[gid] = {
      composite:         breakdowns.reduce((a, b) => a + b.composite, 0) / breakdowns.length,
      valuesCohesion:    breakdowns.reduce((a, b) => a + b.valuesCohesion, 0) / breakdowns.length,
      dominanceBalance:  breakdowns.reduce((a, b) => a + b.dominanceBalance, 0) / breakdowns.length,
      pairCompatibility: breakdowns.reduce((a, b) => a + b.pairCompatibility, 0) / breakdowns.length,
    }
  }

  const getOverCapacity = (gid: string): number => {
    if (!isFrozen || !groupSizeLimit) return 0
    const current = nodesByGroup[gid]?.length ?? 0
    return Math.max(0, current - groupSizeLimit)
  }

  return (
    <svg
      ref={svgRef}
      width={width}
      height={height}
      style={{ display: 'block', touchAction: 'none' }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClearSelection?.()
      }}
    >
      {/* Hulls rendered below nodes */}
      {layout.map((gl) => (
        <GroupHull
          key={gl.group_id}
          nodes={nodesByGroup[gl.group_id] ?? []}
          color={gl.color}
          label={gl.group_id}
          fitBreakdown={groupFitBreakdown[gl.group_id]}
          viewMode={viewMode}
          overCapacity={getOverCapacity(gl.group_id)}
          onDragHandlePointerDown={makeHullDragHandler(gl.group_id)}
        />
      ))}

      {/* Dustbin drop zone — visible only while dragging a group handle */}
      {draggingGroupId && (
        <g transform={`translate(${width - 72}, ${height - 72})`}>
          <rect
            width={58}
            height={58}
            rx={8}
            fill={isOverDustbin ? '#7f1d1d' : '#1e293b'}
            stroke="#ef4444"
            strokeWidth={1.5}
          />
          {/* Trash icon: lid + body + slots */}
          <rect x={18} y={10} width={22} height={6} rx={1.5} fill="none" stroke="#ef4444" strokeWidth={1.5} />
          <rect x={13} y={18} width={32} height={24} rx={2} fill="none" stroke="#ef4444" strokeWidth={1.5} />
          <line x1={23} y1={23} x2={23} y2={37} stroke="#ef4444" strokeWidth={1.2} />
          <line x1={29} y1={23} x2={29} y2={37} stroke="#ef4444" strokeWidth={1.2} />
          <line x1={35} y1={23} x2={35} y2={37} stroke="#ef4444" strokeWidth={1.2} />
        </g>
      )}

      {/* Nodes rendered above hulls */}
      {nodes.map((node) => (
        <AttendeeNode
          key={node.pipeline_user_id}
          node={node}
          color={fitColor(fitScore(node, node.group_id, nodes, activeProfile, pairScores))}
          groupColor={groupIdentityColor(node.group_id)}
          onDragStart={handleDragStart}
          isFrozen={isFrozen}
          isApproved={node.isApproved}
          isStraggler={node.isStraggler}
        />
      ))}
    </svg>
  )
}
