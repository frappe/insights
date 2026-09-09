// Where each cell of a dashboard grid sits.
//
// The reader's grid runs this to draw a saved layout. The author's grid runs it
// on every pointer move, to work out what a drag did to the cells around it.
// Neither surface holds a rule the other does not.
//
// It reads the stored layout alone — no element, no measurement, no pointer. A
// test runs it without a DOM, and the pixels stay in the components.

import type {
	BreakpointKey,
	Layout,
	WorkbookDashboardItemLayout,
} from '../types/workbook.types'

/** Height of one grid row in px. */
export const ROW_HEIGHT = 54

/** Columns a dashboard grid places against. */
export const GRID_COLUMNS = 20

/**
 * Rank a cell by where it sits: top row first, left to right within a row.
 *
 * Charts reach the execution queue in whatever order their documents load, so
 * both surfaces rank them by grid position instead.
 */
export function layoutRank(layout: Layout) {
	return layout.y * GRID_COLUMNS + layout.x
}

function overlaps(a: Layout, b: Layout) {
	return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y
}

/**
 * Pull every cell up until it rests on the one above it or on the top.
 *
 * A stored layout is not always compact. The builder writes the flag the reader
 * obeys, and an author can turn compaction on after laying a grid out loosely,
 * so the gaps have to close here rather than at save time.
 */
export function compactLayouts(layouts: Layout[]): Layout[] {
	const placed: Layout[] = []
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

/** Stack every cell full width, in reading order. */
export function stackLayouts(layouts: Layout[], columns = GRID_COLUMNS): Layout[] {
	let y = 0
	return [...layouts]
		.sort((a, b) => a.y - b.y || a.x - b.x)
		.map((item) => {
			const placed = { ...item, x: 0, y, w: columns }
			y += item.h
			return placed
		})
}

/**
 * Settle a grid the author has just disturbed. The `pinned` cell keeps the place
 * the pointer gave it, and every cell it lands on moves down.
 *
 * The caller passes the grid as it stood when the drag began, with the pinned
 * cell moved to the pointer. The result is then a function of where the pointer
 * is, not of how it got there. A slow drag cannot ratchet the other cells down.
 *
 * Cells come back in the order they went in, because the caller matches them to
 * its own items by position.
 */
export function resolveLayouts(
	layouts: Layout[],
	options: { pinned?: string; verticalCompact?: boolean },
): Layout[] {
	const order = [...layouts].sort((a, b) => {
		if (a.i === options.pinned) return -1
		if (b.i === options.pinned) return 1
		return a.y - b.y || a.x - b.x
	})

	const settled: Layout[] = []
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
	cells: Record<string, Layout>
}

/**
 * Place every cell of one breakpoint's layout.
 *
 * Keyed by identity rather than returned as a list, because the caller draws its
 * cells in the order its own items carry — the slot index has to keep meaning
 * what it meant.
 */
export function placeGrid(
	layouts: Layout[],
	options: { columns: number; verticalCompact?: boolean },
): GridPlacement {
	const placed = options.verticalCompact ? compactLayouts(layouts) : layouts

	const cells: Record<string, Layout> = {}
	for (const item of placed) cells[item.i] = item

	return { columns: options.columns, cells }
}

// ------------------------------------------------------------- breakpoints

export type Breakpoint = {
	key: BreakpointKey
	/** The widest grid this layout is drawn on. The last row has no ceiling. */
	maxWidth: number
	/** Columns this layout places against. */
	columns: number
	/** What an author picking this layout to arrange is offered, untranslated. */
	label: string
	/** The same, by lucide name. */
	icon: string
	/** Build the layout nobody arranged, out of the next wider one. */
	derive?: (layouts: Layout[], columns: number) => Layout[]
}

/**
 * Every width a dashboard is laid out for, narrowest first.
 *
 * A new breakpoint is a row here, and a row is the whole of it: the grid picks
 * the row its own box falls in, an author's drag is stored under that row's key,
 * and an item with nothing stored under it is placed by `derive`. Nothing else
 * in the app decides anything by width.
 */
export const BREAKPOINTS: Breakpoint[] = [
	{
		key: 'sm',
		maxWidth: 600,
		columns: GRID_COLUMNS,
		label: 'Narrow',
		icon: 'lucide-smartphone',
		derive: stackLayouts,
	},
	{
		key: 'lg',
		maxWidth: Infinity,
		columns: GRID_COLUMNS,
		label: 'Wide',
		icon: 'lucide-monitor',
	},
]

/**
 * The breakpoint every item stores a placement for, and the one the others are
 * derived from. The widest: it is the layout an author arranges first, and the
 * only one a dashboard written before there was more than one width holds.
 */
export const BASE_BREAKPOINT = BREAKPOINTS[BREAKPOINTS.length - 1]

export function breakpointFor(width: number): Breakpoint {
	// An unmeasured grid is not a narrow one. Collapsing on a width of zero
	// would stack every card for a frame and lay their contents out twice.
	if (width <= 0) return BASE_BREAKPOINT
	return BREAKPOINTS.find((breakpoint) => width <= breakpoint.maxWidth) || BASE_BREAKPOINT
}

/**
 * One breakpoint's layout, for every item, in the order the items came in.
 *
 * An item that stores a placement for this breakpoint gets it. An item that does
 * not is placed by the breakpoint's `derive`, out of the layout it inherits from
 * the next wider one — which is why a dashboard nobody has arranged for a narrow
 * grid still reads on one, and why a card added on a wide grid turns up on the
 * narrow one too.
 */
export function placementsFor(
	items: WorkbookDashboardItemLayout[],
	key: BreakpointKey,
): Layout[] {
	const index = BREAKPOINTS.findIndex((breakpoint) => breakpoint.key === key)
	const breakpoint = BREAKPOINTS[index]
	if (!breakpoint || breakpoint === BASE_BREAKPOINT) return items.map((item) => item.layout)

	const inherited = placementsFor(items, BREAKPOINTS[index + 1].key)
	const derived = breakpoint.derive
		? breakpoint.derive(inherited, breakpoint.columns)
		: inherited
	const byId = new Map(derived.map((layout) => [layout.i, layout]))

	const merged = items.map((item, position) => {
		const stored = item.layouts?.[key]
		if (!stored) return byId.get(item.layout.i) || inherited[position]
		return { ...stored, i: item.layout.i }
	})

	// An item added after this breakpoint was arranged is placed among cells that
	// know nothing about it. Settling drops whatever lands on something below it,
	// and leaves every cell that clears the others where its author put it.
	return resolveLayouts(merged, { verticalCompact: false })
}

/**
 * Store where one item sits at one breakpoint. The only writer of either field.
 *
 * The widest breakpoint is stored on its own, in `layout`, so identity has one
 * home: a narrower breakpoint stores a box and nothing else.
 */
export function writePlacement(
	item: WorkbookDashboardItemLayout,
	key: BreakpointKey,
	layout: Layout,
) {
	if (key === BASE_BREAKPOINT.key) {
		item.layout = layout
		return
	}
	const { i, ...placement } = layout
	item.layouts = { ...item.layouts, [key]: placement }
}
