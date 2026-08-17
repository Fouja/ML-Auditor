import { create } from 'zustand';

interface UiState {
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
}

// Keep the initial value stable across server and client renders so the SSR
// markup always matches hydration (reading window.innerWidth here would make
// the client render differently than the server on mobile). The real viewport
// width is reconciled in a client effect after mount (see Sidebar).
export const useUiStore = create<UiState>((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}));
