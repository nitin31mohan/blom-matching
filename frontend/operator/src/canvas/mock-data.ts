import type { GroupAssignment, Attendee, MockEvent, GroupLayout } from '../types'

export const MOCK_EVENTS: MockEvent[] = [
  { name: 'Pub quiz — March 2026',          activityType: 'pub_quiz',       socialIntent: 'social'  },
  { name: 'HIIT & mocktails — April 2026',  activityType: 'hiit_mocktails', socialIntent: 'social'  },
  { name: 'Life drawing — May 2026',        activityType: 'life_drawing',   socialIntent: 'singles' },
]

// Group identity layout — group_id → identity color + relative canvas center
export const DEFAULT_GROUP_LAYOUT: GroupLayout[] = [
  { group_id: 'group-a', color: '#8b5cf6', cx: 0.25, cy: 0.40 },
  { group_id: 'group-b', color: '#0ea5e9', cx: 0.58, cy: 0.35 },
  { group_id: 'group-c', color: '#f97316', cx: 0.78, cy: 0.58 },
  { group_id: 'group-d', color: '#10b981', cx: 0.38, cy: 0.72 },
]
// Backward-compat alias — ForceCanvas imports this for its prop type
export const GROUP_LAYOUT = DEFAULT_GROUP_LAYOUT

// 20 attendees in 4 groups of 5
// Trait vectors: [Social energy, Openness, Conscientiousness, Agreeableness, Eco values] — values in [1,5]
// group-a: cohesive high-openness, high-agreeableness → mostly green
// group-c: mixed traits → some amber/red nodes on first load
export const MOCK_ATTENDEES: Attendee[] = [
  // group-a (purple) — cohesive: high openness + agreeableness
  { pipeline_user_id: 'u-aisha',  display_name: 'Aisha',  group_id: 'group-a', traits: [4, 5, 3, 5, 4] },
  { pipeline_user_id: 'u-ben',    display_name: 'Ben',    group_id: 'group-a', traits: [3, 5, 4, 4, 5] },
  { pipeline_user_id: 'u-cleo',   display_name: 'Cleo',   group_id: 'group-a', traits: [4, 4, 3, 5, 4] },
  { pipeline_user_id: 'u-dev',    display_name: 'Dev',    group_id: 'group-a', traits: [5, 4, 4, 4, 3] },
  { pipeline_user_id: 'u-elena',  display_name: 'Elena',  group_id: 'group-a', traits: [3, 5, 3, 5, 5] },

  // group-b (sky) — moderate cohesion: balanced profiles
  { pipeline_user_id: 'u-finn',   display_name: 'Finn',   group_id: 'group-b', traits: [4, 3, 5, 3, 2] },
  { pipeline_user_id: 'u-grace',  display_name: 'Grace',  group_id: 'group-b', traits: [3, 3, 5, 4, 2] },
  { pipeline_user_id: 'u-hiro',   display_name: 'Hiro',   group_id: 'group-b', traits: [5, 2, 5, 3, 3] },
  { pipeline_user_id: 'u-isla',   display_name: 'Isla',   group_id: 'group-b', traits: [4, 3, 4, 4, 2] },
  { pipeline_user_id: 'u-jax',    display_name: 'Jax',    group_id: 'group-b', traits: [3, 4, 5, 3, 3] },

  // group-c (orange) — mixed: intentionally divergent → amber/red nodes
  { pipeline_user_id: 'u-kira',   display_name: 'Kira',   group_id: 'group-c', traits: [5, 5, 1, 2, 5] },
  { pipeline_user_id: 'u-leo',    display_name: 'Leo',    group_id: 'group-c', traits: [1, 2, 5, 5, 1] },
  { pipeline_user_id: 'u-maya',   display_name: 'Maya',   group_id: 'group-c', traits: [4, 4, 2, 1, 4] },
  { pipeline_user_id: 'u-nour',   display_name: 'Nour',   group_id: 'group-c', traits: [2, 3, 4, 4, 2] },
  { pipeline_user_id: 'u-omar',   display_name: 'Omar',   group_id: 'group-c', traits: [5, 1, 3, 2, 5] },

  // group-d (emerald) — moderate: eco-focused with varied social energy
  { pipeline_user_id: 'u-pia',    display_name: 'Pia',    group_id: 'group-d', traits: [2, 4, 4, 3, 5] },
  { pipeline_user_id: 'u-quinn',  display_name: 'Quinn',  group_id: 'group-d', traits: [3, 3, 4, 4, 5] },
  { pipeline_user_id: 'u-raj',    display_name: 'Raj',    group_id: 'group-d', traits: [4, 4, 3, 3, 4] },
  { pipeline_user_id: 'u-sara',   display_name: 'Sara',   group_id: 'group-d', traits: [2, 4, 5, 4, 5] },
  { pipeline_user_id: 'u-theo',   display_name: 'Theo',   group_id: 'group-d', traits: [3, 3, 3, 4, 4] },
]

export const MOCK_STRAGGLERS: Attendee[] = [
  {
    pipeline_user_id: 'straggler-001',
    display_name: 'Late Priya',
    group_id: '',       // filled by placeAllStragglers
    traits: [3, 4, 2, 4, 3],
  },
  {
    pipeline_user_id: 'straggler-002',
    display_name: 'Belated Finn',
    group_id: '',
    traits: [5, 2, 4, 2, 2],
  },
  {
    pipeline_user_id: 'straggler-003',
    display_name: 'Tardy Rosa',
    group_id: '',
    traits: [2, 5, 3, 5, 5],
  },
]

export const MOCK_ASSIGNMENT: GroupAssignment = {
  event_id: 'mock-event-01',
  groups: [
    {
      group_id: 'group-a',
      user_ids: MOCK_ATTENDEES.filter(a => a.group_id === 'group-a').map(a => a.pipeline_user_id),
      cohesion_score: 0.0,
      fit_color: '#8b5cf6',
      flags: [],
    },
    {
      group_id: 'group-b',
      user_ids: MOCK_ATTENDEES.filter(a => a.group_id === 'group-b').map(a => a.pipeline_user_id),
      cohesion_score: 0.0,
      fit_color: '#0ea5e9',
      flags: [],
    },
    {
      group_id: 'group-c',
      user_ids: MOCK_ATTENDEES.filter(a => a.group_id === 'group-c').map(a => a.pipeline_user_id),
      cohesion_score: 0.0,
      fit_color: '#f97316',
      flags: [],
    },
    {
      group_id: 'group-d',
      user_ids: MOCK_ATTENDEES.filter(a => a.group_id === 'group-d').map(a => a.pipeline_user_id),
      cohesion_score: 0.0,
      fit_color: '#10b981',
      flags: [],
    },
  ],
  assigned_at: new Date().toISOString(),
  unassigned: [],
}
