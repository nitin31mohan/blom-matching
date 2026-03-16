import { create } from 'zustand'
import type { Attendee, GroupLayout } from '../types'

interface AlgorithmGroups {
  attendees: Attendee[]
  groupLayout: GroupLayout[]
}

interface CanvasState {
  selectedAttendeeId: string | null
  selectAttendee: (id: string) => void
  clearSelection: () => void
  // Immutable stash — set once on API load; never on drag/delete/reset
  algorithmGroups: AlgorithmGroups | null
  setAlgorithmGroups: (groups: AlgorithmGroups) => void
}

export const useCanvasStore = create<CanvasState>((set) => ({
  selectedAttendeeId: null,
  selectAttendee: (id) => set({ selectedAttendeeId: id }),
  clearSelection: () => set({ selectedAttendeeId: null }),
  algorithmGroups: null,
  setAlgorithmGroups: (groups) => set({ algorithmGroups: groups }),
}))
