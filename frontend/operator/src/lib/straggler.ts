import { fitScore } from './fit'
import type { Attendee, ActivityProfile, PairScoreMap } from '../types'

export function placeAllStragglers(
  stragglers: Attendee[],
  frozenAttendees: Attendee[],
  groupIds: string[],
  activeProfile: ActivityProfile,
  pairScores: PairScoreMap,
  maxGroupSize?: number,  // hard cap — groups at or above this size are skipped
): Attendee[] {
  // Returns stragglers with group_id filled in; frozenAttendees never mutated
  let current = [...frozenAttendees]
  const placed: Attendee[] = []
  for (const s of stragglers) {
    const groupSize = (gid: string) => current.filter(a => a.group_id === gid).length

    // Candidate groups: those below the hard cap (or all groups if no cap / all full)
    const candidates = maxGroupSize !== undefined
      ? (groupIds.filter(gid => groupSize(gid) < maxGroupSize).length > 0
          ? groupIds.filter(gid => groupSize(gid) < maxGroupSize)
          : [...groupIds].sort((a, b) => groupSize(a) - groupSize(b)).slice(0, 1))  // fallback: least-full
      : groupIds

    let bestGroupId = candidates[0]
    let bestScore = -Infinity
    for (const groupId of candidates) {
      const testNodes = [...current, { ...s, group_id: groupId }]
      const score = fitScore(
        { pipeline_user_id: s.pipeline_user_id, traits: s.traits },
        groupId,
        testNodes,
        activeProfile,
        pairScores,
      )
      if (score > bestScore) {
        bestScore = score
        bestGroupId = groupId
      }
    }
    const placed_s: Attendee = { ...s, group_id: bestGroupId, isStraggler: true }
    current = [...current, placed_s]
    placed.push(placed_s)
  }
  return placed
}
