import { useState, useEffect, useMemo } from 'react'
import ForceCanvas from './canvas/ForceCanvas'
import { DEMO_EVENTS, DEMO_GROUP_LAYOUT, DEMO_ATTENDEES } from './data/demo-seed'
import { getActivityProfile } from './lib/activity-profiles'
import { fitScoreDetailed, fitColor, fitLabel, TRAIT_KEYS } from './lib/fit'
import type { Attendee, SimNode, MockEvent, GroupAssignment, ActivityProfile } from './types'

const SIDEBAR_WIDTH = 300
const HEADER_HEIGHT = 60

const ALGO_EXPLAINER = [
  {
    title: 'Values cohesion',
    color: '#8b5cf6',
    body: 'How similar are group members on openness, agreeableness, and eco values? High cohesion = shared worldview.',
  },
  {
    title: 'Dominance balance',
    color: '#0ea5e9',
    body: 'Social events: is the catalyst-to-introvert ratio near the ideal? Singles events: how evenly matched is assertiveness?',
  },
  {
    title: 'Pair compatibility',
    color: '#10b981',
    body: 'Do any attendees have prior feedback history with each other? Positive past interactions = compatibility boost.',
  },
]

export default function App() {
  const [dims, setDims] = useState({ w: window.innerWidth, h: window.innerHeight })
  const [selectedEvent, setSelectedEvent] = useState<MockEvent>(DEMO_EVENTS[0])
  const [attendees, setAttendees] = useState<Attendee[]>(DEMO_ATTENDEES)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'simple' | 'detailed'>('simple')
  const [resetKey, setResetKey] = useState(0)

  const activeProfile = getActivityProfile(selectedEvent)

  // Stable reference — ForceCanvas re-simulates when this changes identity
  const dummyAssignment = useMemo<GroupAssignment>(
    () => ({ event_id: selectedEvent.name, groups: [], assigned_at: '', unassigned: [] }),
    [selectedEvent.name]
  )

  useEffect(() => {
    const onResize = () => setDims({ w: window.innerWidth, h: window.innerHeight })
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  const handleEventChange = (name: string) => {
    const ev = DEMO_EVENTS.find(e => e.name === name) ?? DEMO_EVENTS[0]
    setSelectedEvent(ev)
    setAttendees(DEMO_ATTENDEES.map(a => ({ ...a })))
    setSelectedId(null)
    setResetKey(k => k + 1)
  }

  const handleReassign = (userId: string, newGroupId: string) => {
    setAttendees(prev => prev.map(a =>
      a.pipeline_user_id === userId ? { ...a, group_id: newGroupId } : a
    ))
  }

  const handleNodeClick = (node: SimNode) => setSelectedId(node.pipeline_user_id)
  const handleClearSelection = () => setSelectedId(null)

  const selectedAttendee = attendees.find(a => a.pipeline_user_id === selectedId) ?? null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100vw', height: '100vh', background: '#0f172a' }}>
      {/* Header */}
      <div style={{
        height: HEADER_HEIGHT,
        background: '#0a1628',
        borderBottom: '1px solid #1e293b',
        padding: '0 20px',
        display: 'flex',
        alignItems: 'center',
        gap: 16,
        flexShrink: 0,
      }}>
        <span style={{ color: '#4ade80', fontSize: 15, fontWeight: 500, fontFamily: 'system-ui, sans-serif' }}>
          Blom — group matching demo
        </span>
        <select
          value={selectedEvent.name}
          onChange={e => handleEventChange(e.target.value)}
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
          {DEMO_EVENTS.map(ev => <option key={ev.name} value={ev.name}>{ev.name}</option>)}
        </select>
        <button
          onClick={() => setViewMode(m => m === 'simple' ? 'detailed' : 'simple')}
          style={{
            background: viewMode === 'detailed' ? '#1e3a5f' : 'transparent',
            border: `1px solid ${viewMode === 'detailed' ? '#3b82f6' : '#334155'}`,
            borderRadius: 6,
            color: viewMode === 'detailed' ? '#60a5fa' : '#64748b',
            fontSize: 12,
            padding: '4px 10px',
            fontFamily: 'system-ui, sans-serif',
            cursor: 'pointer',
          }}
        >
          {viewMode === 'simple' ? 'Simple view' : 'Detailed view'}
        </button>
        <span style={{ color: '#475569', fontSize: 12, fontFamily: 'system-ui, sans-serif' }}>
          {attendees.length} attendees · drag to reassign · click for traits
        </span>
      </div>

      {/* Main */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Canvas */}
        <div style={{ flex: 1, overflow: 'hidden' }}>
          <ForceCanvas
            key={resetKey}
            assignment={dummyAssignment}
            attendees={attendees}
            layout={DEMO_GROUP_LAYOUT}
            width={dims.w - SIDEBAR_WIDTH}
            height={dims.h - HEADER_HEIGHT - 32}
            onNodeClick={handleNodeClick}
            onClearSelection={handleClearSelection}
            onReassign={handleReassign}
            activeProfile={activeProfile}
            pairScores={{}}
            viewMode={viewMode}
            isFrozen={false}
          />
        </div>

        {/* Right panel */}
        <div style={{
          width: SIDEBAR_WIDTH,
          background: '#0a1628',
          borderLeft: '1px solid #1e293b',
          padding: 20,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 16,
          fontFamily: 'system-ui, sans-serif',
        }}>
          {selectedAttendee ? (
            <SelectedPanel
              attendee={selectedAttendee}
              attendees={attendees}
              profile={activeProfile}
              groupColor={DEMO_GROUP_LAYOUT.find(g => g.group_id === selectedAttendee.group_id)?.color ?? '#94a3b8'}
            />
          ) : (
            <AlgoExplainer />
          )}
        </div>
      </div>

      {/* Hint bar */}
      <div style={{
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
      }}>
        Throw a node — it bounces back. Drag into another group to reassign.
      </div>
    </div>
  )
}

function AlgoExplainer() {
  return (
    <>
      <p style={{ color: '#94a3b8', fontSize: 13, margin: 0, lineHeight: 1.6 }}>
        The algorithm scores each attendee on three axes and assigns them to the group with the highest combined fit.
      </p>
      {ALGO_EXPLAINER.map(({ title, color, body }) => (
        <div key={title} style={{ borderLeft: `3px solid ${color}`, paddingLeft: 12 }}>
          <p style={{ color, fontSize: 12, fontWeight: 600, margin: '0 0 4px' }}>{title}</p>
          <p style={{ color: '#64748b', fontSize: 12, margin: 0, lineHeight: 1.5 }}>{body}</p>
        </div>
      ))}
      <p style={{ color: '#334155', fontSize: 11, margin: 0, marginTop: 8 }}>
        Node colour: green = great fit · amber = okay · red = mismatch
      </p>
    </>
  )
}

function SelectedPanel({
  attendee,
  attendees,
  profile,
  groupColor,
}: {
  attendee: Attendee
  attendees: Attendee[]
  profile: ActivityProfile
  groupColor: string
}) {
  const breakdown = fitScoreDetailed(attendee, attendee.group_id, attendees, profile, {})

  return (
    <>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ width: 12, height: 12, borderRadius: '50%', background: fitColor(breakdown.composite), flexShrink: 0 }} />
        <span style={{ color: '#e2e8f0', fontSize: 14, fontWeight: 600 }}>{attendee.display_name}</span>
      </div>

      <div style={{ background: '#1e293b', borderRadius: 6, padding: '8px 12px' }}>
        <p style={{ color: '#64748b', fontSize: 11, margin: '0 0 4px' }}>Group fit</p>
        <p style={{ color: fitColor(breakdown.composite), fontSize: 18, fontWeight: 700, margin: 0 }}>
          {Math.round(breakdown.composite * 100)}% — {fitLabel(breakdown.composite)}
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {([
          { label: 'Values cohesion',    val: breakdown.valuesCohesion    },
          { label: 'Dominance balance',  val: breakdown.dominanceBalance  },
          { label: 'Pair compatibility', val: breakdown.pairCompatibility },
        ] as const).map(({ label, val }) => (
          <div key={label}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
              <span style={{ color: '#64748b', fontSize: 11 }}>{label}</span>
              <span style={{ color: fitColor(val), fontSize: 11 }}>{Math.round(val * 100)}%</span>
            </div>
            <div style={{ height: 4, background: '#1e293b', borderRadius: 2 }}>
              <div style={{ height: '100%', width: `${val * 100}%`, background: fitColor(val), borderRadius: 2 }} />
            </div>
          </div>
        ))}
      </div>

      <div style={{ borderTop: '1px solid #1e293b', paddingTop: 12 }}>
        <p style={{ color: '#475569', fontSize: 11, margin: '0 0 8px', fontWeight: 600 }}>Traits</p>
        {TRAIT_KEYS.map((key, i) => (
          <div key={key} style={{ marginBottom: 6 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
              <span style={{ color: '#64748b', fontSize: 11 }}>{key}</span>
              <span style={{ color: '#94a3b8', fontSize: 11 }}>{attendee.traits[i]}/5</span>
            </div>
            <div style={{ height: 3, background: '#1e293b', borderRadius: 2 }}>
              <div style={{
                height: '100%',
                width: `${(attendee.traits[i] / 5) * 100}%`,
                background: groupColor,
                borderRadius: 2,
                opacity: 0.7,
              }} />
            </div>
          </div>
        ))}
      </div>
    </>
  )
}
