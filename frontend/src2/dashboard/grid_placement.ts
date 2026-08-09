// Where each cell of a dashboard grid sits.
//
// This is the whole layout engine a dashboard has. Both surfaces run it: the
// reader's grid to draw a saved layout, and the author's grid on every pointer
// move to work out what a drag has done to the cells around it. Neither one
// owns a rule the other does not, so a reader cannot tell which surface drew
// the grid, and an author sees while dragging exactly what will be saved.
//
// It is a function of the stored layout alone — no element, no measurement, no
// pointer — so it is tested without a DOM. The pixels stay in the components.

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
 * Below this container width the grid collapses to one column. Read against the
 * grid's own box, not the viewport, so a dashboard in a narrow desk panel
 * collapses the same as one on a phone.
 */
export const SINGLE_COLUMN_MAX_WIDTH = 768

/** Height of one grid row in px. */
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

/**
 * Settle a grid the author has just disturbed: put one cell where they dragged
 * it, and push whatever it landed on out of the way.
 *
 * `pinned` is the cell under the pointer. It is placed first and so wins every
 * overlap — everything else settles around it. The rest keep their reading
 * order, top row first, so a cell pushed aside lands where the author expects
 * and does not swap places with its neighbour half way through a drag.
 *
 * The caller passes the grid as it stood when the drag began, with the pinned
 * cell moved to where the pointer is now. That makes the result a function of
 * where the pointer is rather than of how it got there: the same position always
 * settles the same way, and a slow drag over a crowded grid cannot ratchet the
 * other cells further and further down.
 *
 * Cells come back in the order they went in, because the caller matches them to
 * its own items by position.
 */
export function resolveLayouts(
	layouts: GridLayoutItem[],
	options: { pinned?: string; verticalCompact?: boolean },
): GridLayoutItem[] {
	const order = [...layouts].sort((a, b) => {
		if (a.i === options.pinned) return -1
		if (b.i === options.pinned) return 1
		return a.y - b.y || a.x - b.x
	})

	const settled: GridLayoutItem[] = []
	for (const item of order) {
		let y = item.y
		// drop past each cell it lands on until it clears them all
		for (
			let hit = settled.find((other) => overlaps({ ...item, y }, other));
			hit;
			hit = settled.find((other) => overlaps({ ...item, y }, other))
		) {
			y = hit.y + hit.h
		}
		settled.push({ ...item, y })
	}

	// A push-down opens gaps above. Closing them is the same rule the reader's
	// grid obeys, so the author is looking at the saved layout the whole time.
	const closed = options.verticalCompact ? compactLayouts(settled) : settled

	const byId = new Map(closed.map((item) => [item.i, item]))
	return layouts.map((item) => byId.get(item.i) || item)
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
