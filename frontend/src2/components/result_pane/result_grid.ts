// What the pane may ask of the grid inside it.
//
// The grid is the host's, filled through `#grid`, so the pane holds no ref to
// it — but the find is the pane's, and jumping to a match is the grid's to do.
// A grid registers itself here on mount and clears itself on unmount, which is
// how one arrives and departs with the body the pane swaps under it.

import type { InjectionKey } from 'vue'

export type ResultGrid = {
	/** Bring a column into view and mark it, for a find that jumped to it. */
	scrollToColumn: (column_name: string) => void
}

export type ResultGridHost = {
	// eslint-disable-next-line no-unused-vars
	setGrid: (grid?: ResultGrid) => void
}

export const RESULT_GRID_HOST = Symbol('resultGridHost') as InjectionKey<ResultGridHost>
