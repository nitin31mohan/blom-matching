import type { Attendee, Group, ActivityProfile, PairScoreMap } from '../types'
import { fitScoreDetailed, fitColor, fitLabel, TRAIT_KEYS } from '../lib/fit'
import { GROUP_LAYOUT } from '../canvas/mock-data'

interface Props {
  attendee: Attendee
  groupColor: string
  allAttendees: Attendee[]
  groups: Group[]
  onMoveToGroup: (groupId: string) => void
  activeProfile: ActivityProfile
  pairScores: PairScoreMap
  viewMode: 'simple' | 'detailed'
}

export default function AttendeeDetail({
  attendee,
  groupColor,
  allAttendees,
  groups,
  onMoveToGroup,
  activeProfile,
  pairScores,
  viewMode,
}: Props) {
  const breakdown = fitScoreDetailed(attendee, attendee.group_id, allAttendees, activeProfile, pairScores)
  const scoreColor = fitColor(breakdown.composite)
  const scoreLabel = fitLabel(breakdown.composite)
  const otherGroups = GROUP_LAYOUT.filter((gl) => gl.group_id !== attendee.group_id)

  const dynamicLabel = activeProfile.socialIntent === 'singles' ? 'Assertiveness match' : 'Group dynamic'

  return (
    <div
      style={{
        background: '#1e293b',
        borderRadius: 8,
        padding: 16,
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      {/* Name + group */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
        <div
          style={{
            width: 12,
            height: 12,
            borderRadius: '50%',
            background: groupColor,
            flexShrink: 0,
          }}
        />
        <span style={{ color: '#f1f5f9', fontSize: 16, fontWeight: 600 }}>
          {attendee.display_name}
        </span>
      </div>
      <div style={{ color: groupColor, fontSize: 12, marginBottom: 12 }}>
        {attendee.group_id}
      </div>

      {/* Fit score badge — composite */}
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          background: scoreColor + '22',
          border: `1px solid ${scoreColor}55`,
          borderRadius: 6,
          padding: '4px 10px',
          marginBottom: viewMode === 'detailed' ? 12 : 16,
        }}
      >
        <div style={{ width: 8, height: 8, borderRadius: '50%', background: scoreColor }} />
        <span style={{ color: scoreColor, fontSize: 12, fontWeight: 600 }}>
          {scoreLabel} — {Math.round(breakdown.composite * 100)}%
        </span>
      </div>

      {/* Detailed fit breakdown */}
      {viewMode === 'detailed' && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ color: '#64748b', fontSize: 11, marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Fit breakdown
          </div>
          {[
            { label: 'Values cohesion', value: breakdown.valuesCohesion },
            { label: dynamicLabel, value: breakdown.dominanceBalance },
            { label: 'Compatibility', value: breakdown.pairCompatibility, noHistory: breakdown.pairCompatibility === 0.5 },
          ].map(({ label, value, noHistory }) => (
            <div key={label} style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                <span style={{ color: '#94a3b8', fontSize: 11 }}>{label}</span>
                <span style={{ color: fitColor(value), fontSize: 11 }}>{Math.round(value * 100)}%</span>
              </div>
              <div style={{ background: '#0f172a', borderRadius: 3, height: 5 }}>
                <div
                  style={{
                    width: `${value * 100}%`,
                    height: '100%',
                    borderRadius: 3,
                    background: fitColor(value),
                    opacity: 0.8,
                  }}
                />
              </div>
              {noHistory && (
                <div style={{ color: '#475569', fontSize: 10, marginTop: 2 }}>
                  No history yet
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Trait bars */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ color: '#64748b', fontSize: 11, marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Traits
        </div>
        {TRAIT_KEYS.map((key, i) => {
          const val = attendee.traits[i] ?? 0
          return (
            <div key={key} style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                <span style={{ color: '#94a3b8', fontSize: 11 }}>{key}</span>
                <span style={{ color: '#cbd5e1', fontSize: 11 }}>{val}</span>
              </div>
              <div style={{ background: '#0f172a', borderRadius: 3, height: 6 }}>
                <div
                  style={{
                    width: `${(val / 5) * 100}%`,
                    height: '100%',
                    borderRadius: 3,
                    background: groupColor,
                    opacity: 0.8,
                  }}
                />
              </div>
            </div>
          )
        })}
      </div>

      {/* Move to group buttons */}
      <div>
        <div style={{ color: '#64748b', fontSize: 11, marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Move to group
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {otherGroups.map((gl) => {
            const g = groups.find((gr) => gr.group_id === gl.group_id)
            const memberCount = g?.user_ids.length ?? 0
            return (
              <button
                key={gl.group_id}
                onClick={() => onMoveToGroup(gl.group_id)}
                style={{
                  background: gl.color + '22',
                  border: `1px solid ${gl.color}55`,
                  borderRadius: 6,
                  padding: '7px 12px',
                  color: gl.color,
                  fontSize: 12,
                  fontWeight: 500,
                  cursor: 'pointer',
                  textAlign: 'left',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  fontFamily: 'system-ui, sans-serif',
                }}
              >
                <span>{gl.group_id}</span>
                <span style={{ opacity: 0.6, fontSize: 11 }}>{memberCount} members</span>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
