import { fitScore } from './fit'
import type { Attendee, ActivityProfile, PairScoreMap } from '../types'

export function placeAllStragglers(
  stragglers: Attendee[],
  frozenAttendees: Attendee[],
  groupIds: string[],
  activeProfile: ActivityProfile,
  pairScores: PairScoreMap,
): Attendee[] {
  // Returns stragglers with group_id filled in; frozenAttendees never mutated
  let current = [...frozenAttendees]
  const placed: Attendee[] = []
  for (const s of stragglers) {
    let bestGroupId = groupIds[0]
    let bestScore = -Infinity
    for (const groupId of groupIds) {
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
