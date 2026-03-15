/** Mirrors Python Group (matching.assignment) */
export interface Group {
  group_id: string
  user_ids: string[]
  cohesion_score: number
  fit_color: string      // hex colour e.g. "#22c55e"
  flags: string[]        // e.g. "high_anxiety_present", "size_warning"
}

/** Mirrors Python GroupAssignment (matching.assignment) */
export interface GroupAssignment {
  event_id: string
  groups: Group[]
  assigned_at: string    // ISO 8601
  unassigned: string[]
}

/** Flat attendee record for canvas rendering */
export interface Attendee {
  pipeline_user_id: string
  display_name: string   // anonymised — operator view only
  group_id: string
  traits: number[]       // 5 values in [1,5] — indexed by TRAIT_KEYS
  isApproved?: boolean   // true after admin approves; drives green ring when frozen
  isStraggler?: boolean  // true when placed via Import; drives yellow pulse
}

/** D3 simulation node — extends Attendee with mutable position fields */
export interface SimNode extends Attendee {
  x: number
  y: number
  vx: number
  vy: number
  fx: number | null      // fixed x when dragging
  fy: number | null      // fixed y when dragging
}

/** 'singles' events optimise for interesting encounters; 'social' for group cohesion */
export type SocialIntent = 'singles' | 'social'

/** Per-activity scoring configuration */
export interface ActivityProfile {
  activityType: string
  socialIntent: SocialIntent
  weights: {
    valuesCohesion: number      // sum with other weights = 1.0
    dominanceBalance: number    // for 'social': catalyst ratio; for 'singles': assertiveness match
    pairCompatibility: number   // from feedback history; neutral (0.5) when unknown
  }
  catalystTarget: number        // optimal fraction of high-assertiveness members (social only)
  catalystWindow: number        // acceptable deviation either side of target
}

/** Single group's canvas layout entry */
export interface GroupLayout {
  group_id: string
  color: string
  cx: number   // relative 0–1 canvas centre
  cy: number
}

/** Event record used in mock data */
export interface MockEvent {
  name: string
  activityType: string
  socialIntent: SocialIntent
}

/** Detailed per-component fit breakdown */
export interface FitBreakdown {
  composite: number         // weighted sum [0,1]
  valuesCohesion: number    // similarity on values/warmth/openness [0,1]
  dominanceBalance: number  // catalyst balance or assertiveness match [0,1]
  pairCompatibility: number // from pair history [0,1]; 0.5 = no history
}

/**
 * Pair-level compatibility scores accumulated from post-event feedback.
 * bad=-1, neutral=0, good=+1. Outer key = rater, inner key = rated.
 * Admin-only; not surfaced to attendees.
 */
export type PairScoreMap = Record<string, Record<string, number>>
