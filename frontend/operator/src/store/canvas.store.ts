import { create } from 'zustand'

interface CanvasState {
  selectedAttendeeId: string | null
  selectAttendee: (id: string) => void
  clearSelection: () => void
}

export const useCanvasStore = create<CanvasState>((set) => ({
  selectedAttendeeId: null,
  selectAttendee: (id) => set({ selectedAttendeeId: id }),
  clearSelection: () => set({ selectedAttendeeId: null }),
}))
