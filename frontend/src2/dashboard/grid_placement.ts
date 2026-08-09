// Where each cell of a dashboard grid sits, worked out without a layout engine.
//
// The editor needs `grid-layout-plus` because it drags and resizes. A reader
// does neither, and the engine costs 136 kB — more than half the dashboard
// island. So a read-only grid places its cells itself, and this is the
// arithmetic it does. It is a function of the stored layout alone, so it is
// tested without a DOM.
//
// The numbers here restate the engine's own behaviour rather than inventing a
// second one: the same compaction rule, and the same single-column collapse at
// the same width. A reader must not be able to tell which surface drew the grid.

/** A cell as the document stores it: a column, a row, and a span of each. */
export type GridLayoutItem = {
	/** The cell's identity, stable across a move. */
	i: string
	x: number
	y: number
	w: number
	h: number
}

/**
 * Below this container width the grid collapses to one column, which is the
 * breakpoint `grid-layout-plus` picks for the `xs` and `xxs` column counts the
 * builder configures. Read against the grid's own box, not the viewport, so a
 * dashboard in a narrow desk panel collapses the same as one on a phone.
 */
export const SINGLE_COLUMN_MAX_WIDTH = 768

/** Height of one grid row in px. The engine's `rowHeight`, restated. */
export const ROW_HEIGHT = 52

function overlaps(a: GridLayoutItem, b: GridLayoutItem) {
	return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y
}

/**
 * Pull every cell up until it rests on the one above it or on the top.
 *
 * A stored layout is not always compact. The builder writes the flag the reader
 * obeys, and an author can turn compaction on after laying a grid out loosely,
 * so the gaps have to close here rather than at save time.
 */
export function compactLayouts(layouts: GridLayoutItem[]): GridLayoutItem[] {
	const placed: GridLayoutItem[] = []
	// top row first, then left to right — a cell can only rest on one already placed
	const order = [...layouts].sort((a, b) => a.y - b.y || a.x - b.x)

	for (const item of order) {
		let y = item.y
		while (y > 0 && !placed.some((other) => overlaps({ ...item, y: y - 1 }, other))) {
			y--
		}
		placed.push({ ...item, y })
	}

	return placed
}

/** Stack every cell full width, in reading order. The one-column collapse. */
export function stackLayouts(layouts: GridLayoutItem[]): GridLayoutItem[] {
	let y = 0
	return [...layouts]
		.sort((a, b) => a.y - b.y || a.x - b.x)
		.map((item) => {
			const placed = { ...item, x: 0, y, w: 1 }
			y += item.h
			return placed
		})
}

export type GridPlacement = {
	/** Column count the cells were placed against. */
	columns: number
	/** Placement by cell identity, so the caller can draw in its own order. */
	cells: Record<string, GridLayoutItem>
}

/**
 * Place every cell, given the grid's width.
 *
 * Keyed by identity rather than returned as a list, because the caller draws its
 * cells in the order its own items carry — the slot index has to keep meaning
 * what it meant.
 */
export function placeGrid(
	layouts: GridLayoutItem[],
	options: { columns: number; width: number; verticalCompact?: boolean },
): GridPlacement {
	const single = options.width > 0 && options.width <= SINGLE_COLUMN_MAX_WIDTH
	const placed = single
		? stackLayouts(layouts)
		: options.verticalCompact
			? compactLayouts(layouts)
			: layouts

	const cells: Record<string, GridLayoutItem> = {}
	for (const item of placed) cells[item.i] = item

	return { columns: single ? 1 : options.columns, cells }
}
