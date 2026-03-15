import type { ActivityProfile, MockEvent } from '../types'

export const ACTIVITY_PROFILES: Record<string, ActivityProfile> = {
  pub_quiz: {
    activityType: 'pub_quiz',
    socialIntent: 'social',
    weights: { valuesCohesion: 0.55, dominanceBalance: 0.25, pairCompatibility: 0.20 },
    catalystTarget: 0.20,   // ~1 in 5 high-assertiveness
    catalystWindow: 0.10,
  },
  hiit_mocktails: {
    activityType: 'hiit_mocktails',
    socialIntent: 'social',
    weights: { valuesCohesion: 0.30, dominanceBalance: 0.50, pairCompatibility: 0.20 },
    catalystTarget: 0.30,   // ~1 in 3 — energy events need more catalysts
    catalystWindow: 0.10,
  },
  life_drawing: {
    activityType: 'life_drawing',
    socialIntent: 'singles',
    weights: { valuesCohesion: 0.30, dominanceBalance: 0.30, pairCompatibility: 0.40 },
    catalystTarget: 0.15,   // unused for singles — assertiveness match is used instead
    catalystWindow: 0.10,
  },
}

export function getActivityProfile(event: MockEvent): ActivityProfile {
  return ACTIVITY_PROFILES[event.activityType] ?? ACTIVITY_PROFILES['pub_quiz']
}
