import { useState, useEffect } from 'react'
import ForceCanvas from './canvas/ForceCanvas'
import { MOCK_ASSIGNMENT, MOCK_ATTENDEES, MOCK_EVENTS, MOCK_STRAGGLERS, DEFAULT_GROUP_LAYOUT } from './canvas/mock-data'
import { placeAllStragglers } from './lib/straggler'
import { useCanvasStore } from './store/canvas.store'
import AttendeeDetail from './panels/AttendeeDetail'
import type { Attendee, SimNode, MockEvent, PairScoreMap, GroupLayout } from './types'
import { getActivityProfile } from './lib/activity-profiles'

const SIDEBAR_WIDTH = 320
const HEADER_HEIGHT = 72

export default function App() {
  const [dims, setDims] = useState({ w: window.innerWidth, h: window.innerHeight })
  const [attendees, setAttendees] = useState<Attendee[]>(MOCK_ATTENDEES)
  const [selectedEvent, setSelectedEvent] = useState<MockEvent>(MOCK_EVENTS[0])
  const [resetKey, setResetKey] = useState(0)
  const [viewMode, setViewMode] = useState<'simple' | 'detailed'>('simple')
  const [pairScores] = useState<PairScoreMap>({})
  const [groupLayout, setGroupLayout] = useState<GroupLayout[]>(DEFAULT_GROUP_LAYOUT)
  const [isFrozen, setIsFrozen] = useState(false)
  const [hasImportedStragglers, setHasImportedStragglers] = useState(false)
  const [groupSizeLimit, setGroupSizeLimit] = useState(5)
  const [groupSizeLimitInput, setGroupSizeLimitInput] = useState('5')
  const [stragglerMessage, setStragglerMessage] = useState<string | null>(null)
  const { clearSelection } = useCanvasStore()
  const { selectedAttendeeId, selectAttendee } = useCanvasStore()

  const activeProfile = getActivityProfile(selectedEvent)

  useEffect(() => {
    const onResize = () => setDims({ w: window.innerWidth, h: window.innerHeight })
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  function approveAssignment(currentAttendees: Attendee[]) {
    const payload = currentAttendees.map(a => ({ userId: a.pipeline_user_id, groupId: a.group_id }))
    console.log('[Blom] approveAssignment →', payload)
    // Phase 06: POST to Supabase — compares against last approved state, notifies diff only
  }

  const handleApprove = () => {
    const snapshot = attendees.map(a => ({ ...a, isApproved: true, isStraggler: false }))
    setAttendees(snapshot)
    setIsFrozen(true)
    setHasImportedStragglers(false)
    approveAssignment(snapshot)
  }

  const handleThaw = () => {
    setIsFrozen(false)
    setHasImportedStragglers(false)
    // Group assignments preserved; lock indicators will not render (isFrozen = false)
  }

  const handleImportStragglers = () => {
    const existingIds = new Set(attendees.map(a => a.pipeline_user_id))
    const incoming = MOCK_STRAGGLERS.filter(s => !existingIds.has(s.pipeline_user_id))
    if (incoming.length === 0) {
      setStragglerMessage('No new sign-ups found.')
      return
    }
    const groupIds = groupLayout.map(gl => gl.group_id)
    const placed = placeAllStragglers(incoming, attendees, groupIds, activeProfile, pairScores)
    setAttendees(prev => [...prev, ...placed])
    setHasImportedStragglers(true)
    setStragglerMessage(`${placed.length} new sign-up${placed.length > 1 ? 's' : ''} found — placed in best-fit groups`)
    setResetKey(k => k + 1)
  }

  const handleReset = () => {
    setAttendees(MOCK_ATTENDEES)
    setGroupLayout(DEFAULT_GROUP_LAYOUT)
    setIsFrozen(false)
    setHasImportedStragglers(false)
    setStragglerMessage(null)
    clearSelection()
    setResetKey((k) => k + 1)
  }

  const handleDeleteGroup = (groupId: string) => {
    const remainingLayout = groupLayout.filter(gl => gl.group_id !== groupId)
    if (remainingLayout.length === 0) return  // cannot delete the last group
    const deletedMembers = attendees.filter(a => a.group_id === groupId)
    const remainingAttendees = attendees.filter(a => a.group_id !== groupId)
    const remainingGroupIds = remainingLayout.map(gl => gl.group_id)
    const placed = placeAllStragglers(
      deletedMembers.map(a => ({ ...a, group_id: '', isApproved: false })),
      remainingAttendees,
      remainingGroupIds,
      activeProfile,
      pairScores,
    )
    setAttendees([...remainingAttendees, ...placed])
    setGroupLayout(remainingLayout)
    setStragglerMessage(
      `Group ${groupId} dissolved — ${placed.length} member${placed.length > 1 ? 's' : ''} redistributed`
    )
    setResetKey(k => k + 1)
  }

  const handleEventChange = (eventName: string) => {
    const event = MOCK_EVENTS.find(e => e.name === eventName) ?? MOCK_EVENTS[0]
    setSelectedEvent(event)
    // In production: fetch attendees + default groupings for the new event
    // For now: reset to mock data so each activity starts clean
    setAttendees(MOCK_ATTENDEES)
    setGroupLayout(DEFAULT_GROUP_LAYOUT)
    setIsFrozen(false)
    setHasImportedStragglers(false)
    setStragglerMessage(null)
    clearSelection()
    setResetKey((k) => k + 1)
  }

  const handleReassign = (userId: string, newGroupId: string) => {
    setAttendees((prev) =>
      prev.map((a) => (a.pipeline_user_id === userId ? { ...a, group_id: newGroupId } : a))
    )
  }

  const handleNodeClick = (node: SimNode) => {
    selectAttendee(node.pipeline_user_id)
  }

  const selectedAttendee = attendees.find((a) => a.pipeline_user_id === selectedAttendeeId) ?? null
  const selectedGroupColor =
    groupLayout.find((gl) => gl.group_id === selectedAttendee?.group_id)?.color ?? '#94a3b8'

  // Derive group counts from live attendees state
  const groupCounts = groupLayout.map((gl) => ({
    ...gl,
    count: attendees.filter((a) => a.group_id === gl.group_id).length,
  }))

  // Sync MOCK_ASSIGNMENT user_ids with live attendees for panel move buttons
  const liveAssignment = {
    ...MOCK_ASSIGNMENT,
    groups: MOCK_ASSIGNMENT.groups.map((g) => ({
      ...g,
      user_ids: attendees.filter((a) => a.group_id === g.group_id).map((a) => a.pipeline_user_id),
    })),
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100vw', height: '100vh', background: '#0f172a', position: 'relative' }}>
      {/* Header */}
      <div
        style={{
          height: HEADER_HEIGHT,
          background: '#0a1628',
          borderBottom: '1px solid #1e293b',
          padding: '0 20px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          gap: 8,
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <span style={{ color: '#4ade80', fontSize: 15, fontWeight: 500, fontFamily: 'system-ui, sans-serif' }}>
            Blom — group canvas
          </span>
          <select
            value={selectedEvent.name}
            onChange={(e) => handleEventChange(e.target.value)}
            style={{
              background: '#1e293b',
              border: '1px solid #334155',
              borderRadius: 6,
              color: '#e2e8f0',
              fontSize: 13,
              padding: '4px 8px',
              fontFamily: 'system-ui, sans-serif',
              cursor: 'pointer',
            }}
          >
            {MOCK_EVENTS.map((ev) => (
              <option key={ev.name} value={ev.name}>{ev.name}</option>
            ))}
          </select>
          <label style={{ display: 'flex', alignItems: 'center', gap: 5, color: '#64748b', fontSize: 12, fontFamily: 'system-ui, sans-serif' }}>
            Max/group:
            <input
              type="number"
              list="group-size-presets"
              min={1}
              max={50}
              value={groupSizeLimitInput}
              onFocus={(e) => e.target.select()}
              onChange={(e) => {
                setGroupSizeLimitInput(e.target.value)
                const v = parseInt(e.target.value, 10)
                if (!isNaN(v) && v > 0) setGroupSizeLimit(v)
              }}
              onBlur={() => {
                const v = parseInt(groupSizeLimitInput, 10)
                setGroupSizeLimitInput(String(!isNaN(v) && v > 0 ? v : groupSizeLimit))
              }}
              style={{
                width: 52,
                background: '#1e293b',
                border: '1px solid #334155',
                borderRadius: 6,
                color: '#e2e8f0',
                fontSize: 12,
                padding: '4px 6px',
                fontFamily: 'system-ui, sans-serif',
              }}
            />
            <datalist id="group-size-presets">
              {[3, 4, 5, 6, 7, 8, 10, 12, 15].map(n => (
                <option key={n} value={n} />
              ))}
            </datalist>
          </label>
          <button
            onClick={() => setViewMode(m => m === 'simple' ? 'detailed' : 'simple')}
            title="Toggle between simple and detailed fit view"
            style={{
              background: viewMode === 'detailed' ? '#1e3a5f' : 'transparent',
              border: `1px solid ${viewMode === 'detailed' ? '#3b82f6' : '#334155'}`,
              borderRadius: 6,
              color: viewMode === 'detailed' ? '#60a5fa' : '#64748b',
              fontSize: 12,
              padding: '4px 10px',
              fontFamily: 'system-ui, sans-serif',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 5,
            }}
          >
            {viewMode === 'simple' ? 'Simple view' : 'Detailed view'}
          </button>
          {/* Freeze — shown when not frozen, or when frozen after import (re-approve) */}
          {(!isFrozen || hasImportedStragglers) && (
            <button onClick={handleApprove} style={{
              background: '#14532d',
              border: '1px solid #22c55e',
              borderRadius: 6, color: '#4ade80',
              fontSize: 12, padding: '4px 10px',
              fontFamily: 'system-ui, sans-serif', cursor: 'pointer',
            }}>
              Freeze
            </button>
          )}
          {/* Unfreeze — shown whenever frozen */}
          {isFrozen && (
            <button onClick={handleThaw} style={{
              background: 'transparent', border: '1px solid #64748b',
              borderRadius: 6, color: '#94a3b8',
              fontSize: 12, padding: '4px 10px',
              fontFamily: 'system-ui, sans-serif', cursor: 'pointer',
            }}>
              Unfreeze
            </button>
          )}
          {/* Import — only shown when frozen and no import has happened yet */}
          {isFrozen && !hasImportedStragglers && (
            <button onClick={handleImportStragglers} style={{
              background: '#1c1917', border: '1px solid #f59e0b',
              borderRadius: 6, color: '#fbbf24',
              fontSize: 12, padding: '4px 10px',
              fontFamily: 'system-ui, sans-serif', cursor: 'pointer',
            }}>
              Import new sign-ups
            </button>
          )}
          <button
            onClick={handleReset}
            title="Reset groupings to defaults for this activity"
            style={{
              background: 'transparent',
              border: '1px solid #334155',
              borderRadius: 6,
              color: '#64748b',
              fontSize: 12,
              padding: '4px 10px',
              fontFamily: 'system-ui, sans-serif',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 5,
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = '#475569'
              e.currentTarget.style.color = '#94a3b8'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = '#334155'
              e.currentTarget.style.color = '#64748b'
            }}
          >
            Reset groupings
          </button>
          <span style={{ color: '#475569', fontSize: 13, fontFamily: 'system-ui, sans-serif' }}>
            {attendees.length} attendees
            {groupCounts.map((gc) => (
              <span key={gc.group_id}>
                {' · '}
                <span style={{ color: gc.color }}>{gc.group_id}: {gc.count}</span>
              </span>
            ))}
          </span>
        </div>

        {/* Fit legend */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, fontSize: 12, fontFamily: 'system-ui, sans-serif' }}>
          {[
            { color: '#22c55e', label: 'Great fit' },
            { color: '#f59e0b', label: 'Okay' },
            { color: '#ef4444', label: 'Mismatch' },
          ].map(({ color, label }) => (
            <span key={label} style={{ display: 'flex', alignItems: 'center', gap: 5, color: '#94a3b8' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: color, display: 'inline-block' }} />
              {label}
            </span>
          ))}
          <span style={{ color: '#334155' }}>·</span>
          <span style={{ color: '#475569' }}>Drag to reassign · Click for details</span>
        </div>
      </div>

      {/* Straggler banner — absolutely positioned so it doesn't affect header or canvas layout */}
      {stragglerMessage && (
        <div style={{
          position: 'absolute',
          top: HEADER_HEIGHT + 8,
          left: 20,
          zIndex: 10,
          display: 'flex', alignItems: 'center', gap: 8,
          background: '#1c1917', border: '1px solid #f59e0b55',
          borderRadius: 6, padding: '6px 12px',
          color: '#fbbf24', fontSize: 12,
          fontFamily: 'system-ui, sans-serif',
        }}>
          <span>{stragglerMessage}</span>
          <button
            onClick={() => setStragglerMessage(null)}
            style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 14, lineHeight: 1 }}
          >×</button>
        </div>
      )}

      {/* Main area */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Canvas */}
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <ForceCanvas
            key={resetKey}
            assignment={liveAssignment}
            attendees={attendees}
            layout={groupLayout}
            width={dims.w - SIDEBAR_WIDTH}
            height={dims.h - HEADER_HEIGHT - 32}
            onNodeClick={handleNodeClick}
            onClearSelection={clearSelection}
            onReassign={handleReassign}
            onDeleteGroup={handleDeleteGroup}
            activeProfile={activeProfile}
            pairScores={pairScores}
            viewMode={viewMode}
            isFrozen={isFrozen}
            groupSizeLimit={groupSizeLimit}
          />
        </div>

        {/* Sidebar */}
        <div
          style={{
            width: SIDEBAR_WIDTH,
            background: '#0a1628',
            borderLeft: '1px solid #1e293b',
            padding: 16,
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
          }}
        >
          {selectedAttendee ? (
            <AttendeeDetail
              attendee={selectedAttendee}
              groupColor={selectedGroupColor}
              allAttendees={attendees}
              groups={liveAssignment.groups}
              onMoveToGroup={(groupId) => {
                handleReassign(selectedAttendee.pipeline_user_id, groupId)
                selectAttendee(selectedAttendee.pipeline_user_id)
              }}
              activeProfile={activeProfile}
              pairScores={pairScores}
              viewMode={viewMode}
            />
          ) : (
            <p
              style={{
                color: '#475569',
                fontSize: 13,
                fontFamily: 'system-ui, sans-serif',
                marginTop: 8,
              }}
            >
              Click an attendee to see details
            </p>
          )}
        </div>
      </div>

      {/* Hint bar */}
      <div
        style={{
          height: 32,
          background: '#0a1628',
          borderTop: '1px solid #1e293b',
          display: 'flex',
          alignItems: 'center',
          paddingLeft: 20,
          color: '#334155',
          fontSize: 12,
          fontFamily: 'system-ui, sans-serif',
          flexShrink: 0,
        }}
      >
        Throw a node — it bounces back. Click any attendee to inspect their profile.
      </div>
    </div>
  )
}
