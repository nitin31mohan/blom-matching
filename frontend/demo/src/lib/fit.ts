import type { ActivityProfile, FitBreakdown, PairScoreMap } from '../types'

export const TRAIT_KEYS = [
  'Social energy',      // index 0 — feeds assertiveness derivation
  'Openness',           // index 1 — similarity axis
  'Conscientiousness',  // index 2 — display only (not used in scoring)
  'Agreeableness',      // index 3 — similarity axis + assertiveness (inverted)
  'Eco values',         // index 4 — similarity axis
] as const

export type TraitKey = (typeof TRAIT_KEYS)[number]

// ── Internal helpers ──────────────────────────────────────────────────────────

/** Mean absolute agreement on a subset of trait indices. [0,1] */
function traitAgreementSubset(a: number[], b: number[], indices: number[]): number {
  if (indices.length === 0) return 1
  const totalDiff = indices.reduce((acc, i) => acc + Math.abs(a[i] - b[i]), 0)
  return 1 - totalDiff / (indices.length * 4)
}

/** Derived assertiveness from Social energy (index 0) + inverse Agreeableness (index 3). [1,5] */
function deriveAssertiveness(traits: number[]): number {
  return traits[0] * 0.6 + (6 - traits[3]) * 0.4
}

// ── Axis A: Values cohesion (similarity on openness/agreeableness/eco) ────────

/** Mean pairwise trait agreement on similarity-axis traits (indices 1, 3, 4). [0,1] */
function computeValuesCohesion(
  nodeTraits: number[],
  groupId: string,
  allNodes: Array<{ pipeline_user_id: string; group_id: string; traits: number[] }>,
  selfId: string,
): number {
  const peers = allNodes.filter(n => n.group_id === groupId && n.pipeline_user_id !== selfId)
  if (peers.length === 0) return 1
  const sims = peers.map(p => traitAgreementSubset(nodeTraits, p.traits, [1, 3, 4]))
  return sims.reduce((a, b) => a + b, 0) / sims.length
}

// ── Axis B: Dominance balance ─────────────────────────────────────────────────

/** Score based on how close the group's catalyst ratio is to the activity target. [0,1] */
function catalystBalance(
  groupNodes: Array<{ traits: number[] }>,
  profile: ActivityProfile,
): number {
  if (groupNodes.length === 0) return 1
  const catalysts = groupNodes.filter(n => deriveAssertiveness(n.traits) > 3.5).length
  const ratio = catalysts / groupNodes.length
  const distance = Math.abs(ratio - profile.catalystTarget)
  if (distance <= profile.catalystWindow) return 1.0
  // Linear decay outside window; reaches 0 at distance = catalystWindow * 2
  return Math.max(0, 1 - (distance - profile.catalystWindow) / profile.catalystWindow)
}

/** Assertiveness matching for singles: low variance = high score. [0,1] */
function assertivenessMatch(groupNodes: Array<{ traits: number[] }>): number {
  if (groupNodes.length <= 1) return 1
  const vals = groupNodes.map(n => deriveAssertiveness(n.traits))
  const mean = vals.reduce((a, b) => a + b, 0) / vals.length
  const variance = vals.reduce((acc, v) => acc + (v - mean) ** 2, 0) / vals.length
  // stdDev max is ~2 on [1,5] scale; normalize to [0,1]
  return Math.max(0, 1 - Math.sqrt(variance) / 2)
}

// ── Axis C: Pair compatibility ────────────────────────────────────────────────

/** Mean of known pair scores for this node within the group. [0,1]; 0.5 = no history. */
function computePairCompatibility(
  nodeId: string,
  groupId: string,
  allNodes: Array<{ pipeline_user_id: string; group_id: string }>,
  pairScores: PairScoreMap,
): number {
  const peers = allNodes.filter(n => n.group_id === groupId && n.pipeline_user_id !== nodeId)
  const knownPairs = peers.filter(p => pairScores[nodeId]?.[p.pipeline_user_id] !== undefined)
  if (knownPairs.length === 0) return 0.5  // neutral: no history
  const sum = knownPairs.reduce((acc, p) => acc + pairScores[nodeId][p.pipeline_user_id], 0)
  // pairScores are -1|0|+1; normalize to [0,1]
  return (sum / knownPairs.length + 1) / 2
}

// ── Public API ────────────────────────────────────────────────────────────────

export function fitScoreDetailed(
  node: { pipeline_user_id: string; traits: number[] },
  groupId: string,
  allNodes: Array<{ pipeline_user_id: string; group_id: string; traits: number[] }>,
  profile: ActivityProfile,
  pairScores: PairScoreMap = {},
): FitBreakdown {
  const groupNodes = allNodes.filter(n => n.group_id === groupId)

  const valuesCohesion = computeValuesCohesion(node.traits, groupId, allNodes, node.pipeline_user_id)
  const dominanceBalance = profile.socialIntent === 'singles'
    ? assertivenessMatch(groupNodes)
    : catalystBalance(groupNodes, profile)
  const pairCompatibility = computePairCompatibility(node.pipeline_user_id, groupId, allNodes, pairScores)

  const { weights: w } = profile
  const composite =
    w.valuesCohesion * valuesCohesion +
    w.dominanceBalance * dominanceBalance +
    w.pairCompatibility * pairCompatibility

  return { composite, valuesCohesion, dominanceBalance, pairCompatibility }
}

/** Returns composite fit score [0,1]. Used for node/hull color. */
export function fitScore(
  node: { pipeline_user_id: string; traits: number[] },
  groupId: string,
  allNodes: Array<{ pipeline_user_id: string; group_id: string; traits: number[] }>,
  profile: ActivityProfile,
  pairScores: PairScoreMap = {},
): number {
  return fitScoreDetailed(node, groupId, allNodes, profile, pairScores).composite
}

export function fitColor(score: number): string {
  if (score > 0.68) return '#22c55e'
  if (score > 0.42) return '#f59e0b'
  return '#ef4444'
}

export function fitLabel(score: number): string {
  if (score > 0.68) return 'Great fit'
  if (score > 0.42) return 'Okay fit'
  return 'Poor fit'
}
