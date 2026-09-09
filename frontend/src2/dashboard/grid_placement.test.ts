import { describe, expect, it } from 'vitest'
import type { Layout, WorkbookDashboardItemLayout } from '../types/workbook.types'
import {
	BASE_BREAKPOINT,
	GRID_COLUMNS,
	breakpointFor,
	compactLayouts,
	placeGrid,
	placementsFor,
	resolveLayouts,
	stackLayouts,
	writePlacement,
} from './grid_placement'

// A cell, named so a case reads as the grid it describes.
function cell(i: string, x: number, y: number, w: number, h: number): Layout {
	return { i, x, y, w, h }
}

// A dashboard item, reduced to the half of it a grid reads.
function item(layout: Layout, layouts = {}): WorkbookDashboardItemLayout {
	return { layout, layouts }
}

const WIDE = 1200
const NARROW = 500

describe('compactLayouts', () => {
	it('rests a cell on the top when nothing is above it', () => {
		expect(compactLayouts([cell('a', 0, 5, 6, 2)])).toEqual([cell('a', 0, 0, 6, 2)])
	})

	it('rests a cell on the one above it, not on the top', () => {
		const compacted = compactLayouts([cell('a', 0, 0, 6, 2), cell('b', 0, 9, 6, 2)])
		expect(compacted).toContainEqual(cell('b', 0, 2, 6, 2))
	})

	it('lets a cell fall past one in another column', () => {
		// 'b' sits to the right of 'a', so nothing blocks it
		const compacted = compactLayouts([cell('a', 0, 0, 6, 4), cell('b', 6, 6, 6, 2)])
		expect(compacted).toContainEqual(cell('b', 6, 0, 6, 2))
	})

	it('keeps a grid that is already compact exactly where it is', () => {
		const grid = [cell('a', 0, 0, 6, 2), cell('b', 6, 0, 6, 2), cell('c', 0, 2, 12, 3)]
		expect(compactLayouts(grid)).toEqual(grid)
	})

	it('leaves the caller its own array', () => {
		const grid = [cell('a', 0, 4, 6, 2)]
		compactLayouts(grid)
		expect(grid).toEqual([cell('a', 0, 4, 6, 2)])
	})
})

describe('stackLayouts', () => {
	it('gives every cell the full width, one under the other', () => {
		const stacked = stackLayouts([cell('a', 0, 0, 6, 2), cell('b', 6, 0, 6, 3)], 12)
		expect(stacked).toEqual([cell('a', 0, 0, 12, 2), cell('b', 0, 2, 12, 3)])
	})

	it('stacks in reading order, top row first and then left to right', () => {
		const stacked = stackLayouts([
			cell('right', 6, 0, 6, 2),
			cell('below', 0, 4, 12, 2),
			cell('left', 0, 0, 6, 2),
		])
		expect(stacked.map((item) => item.i)).toEqual(['left', 'right', 'below'])
	})
})

describe('resolveLayouts', () => {
	// the cell under the pointer, and the grid it was dropped onto
	const dragged = (x: number, y: number) => cell('dragged', x, y, 6, 2)

	it('leaves the dragged cell where the pointer put it', () => {
		const settled = resolveLayouts([dragged(0, 0), cell('b', 0, 0, 6, 2)], {
			pinned: 'dragged',
			verticalCompact: false,
		})
		expect(settled[0]).toEqual(dragged(0, 0))
	})

	it('pushes the cell it landed on out from under it', () => {
		const settled = resolveLayouts([dragged(0, 0), cell('b', 0, 0, 6, 2)], {
			pinned: 'dragged',
			verticalCompact: false,
		})
		expect(settled[1]).toEqual(cell('b', 0, 2, 6, 2))
	})

	it('leaves a cell it did not land on alone', () => {
		const settled = resolveLayouts([dragged(0, 0), cell('right', 6, 0, 6, 2)], {
			pinned: 'dragged',
			verticalCompact: false,
		})
		expect(settled[1]).toEqual(cell('right', 6, 0, 6, 2))
	})

	it('cascades a push down through the cells below', () => {
		const settled = resolveLayouts(
			[dragged(0, 0), cell('b', 0, 0, 6, 2), cell('c', 0, 2, 6, 2)],
			{ pinned: 'dragged', verticalCompact: false },
		)
		expect(settled[1]).toEqual(cell('b', 0, 2, 6, 2))
		expect(settled[2]).toEqual(cell('c', 0, 4, 6, 2))
	})

	it('closes the gap a push opened when the dashboard asks for compaction', () => {
		// nothing is dropped on 'low', so compaction pulls it to the top
		const settled = resolveLayouts([dragged(6, 0), cell('low', 0, 8, 6, 2)], {
			pinned: 'dragged',
			verticalCompact: true,
		})
		expect(settled[1]).toEqual(cell('low', 0, 0, 6, 2))
	})

	it('rests a pushed cell under the dragged one, not back on top of it', () => {
		const settled = resolveLayouts([dragged(0, 0), cell('b', 0, 0, 6, 2)], {
			pinned: 'dragged',
			verticalCompact: true,
		})
		expect(settled[1]).toEqual(cell('b', 0, 2, 6, 2))
	})

	it('settles the same way however the pointer arrived', () => {
		const grid = [dragged(0, 4), cell('b', 0, 0, 6, 2), cell('c', 0, 2, 6, 2)]
		const options = { pinned: 'dragged', verticalCompact: true }
		// resolving a settled grid again must not push anything further down
		expect(resolveLayouts(resolveLayouts(grid, options), options)).toEqual(
			resolveLayouts(grid, options),
		)
	})

	it('hands the cells back in the order it got them', () => {
		const settled = resolveLayouts([cell('c', 0, 9, 6, 2), cell('a', 0, 0, 6, 2)], {
			verticalCompact: true,
		})
		expect(settled.map((item) => item.i)).toEqual(['c', 'a'])
	})

	it('leaves the caller its own array', () => {
		const grid = [dragged(0, 0), cell('b', 0, 0, 6, 2)]
		resolveLayouts(grid, { pinned: 'dragged', verticalCompact: true })
		expect(grid[1]).toEqual(cell('b', 0, 0, 6, 2))
	})
})

describe('placeGrid', () => {
	it('keys every cell by its identity, so the caller can draw in its own order', () => {
		const placed = placeGrid([cell('a', 0, 0, 6, 2), cell('b', 6, 0, 6, 2)], { columns: 12 })
		expect(Object.keys(placed.cells).sort()).toEqual(['a', 'b'])
	})

	it('places against the columns it is given', () => {
		const placed = placeGrid([cell('a', 0, 0, 6, 2)], { columns: 12 })
		expect(placed.columns).toBe(12)
	})

	it('closes the gaps when the dashboard asks for compaction', () => {
		const placed = placeGrid([cell('a', 0, 7, 6, 2)], { columns: 12, verticalCompact: true })
		expect(placed.cells.a.y).toBe(0)
	})

	it('leaves the gaps where the dashboard does not', () => {
		const placed = placeGrid([cell('a', 0, 7, 6, 2)], { columns: 12, verticalCompact: false })
		expect(placed.cells.a.y).toBe(7)
	})
})

describe('breakpointFor', () => {
	it('reads a narrow grid as the narrow breakpoint', () => {
		expect(breakpointFor(NARROW).key).toBe('sm')
	})

	it('reads a wide grid as the widest breakpoint', () => {
		expect(breakpointFor(WIDE)).toBe(BASE_BREAKPOINT)
	})

	// The grid reports zero before it has been measured. Collapsing then would
	// draw the narrow layout for a frame and reflow, which reads as a break.
	it('reads an unmeasured grid as the widest breakpoint', () => {
		expect(breakpointFor(0)).toBe(BASE_BREAKPOINT)
	})
})

describe('placementsFor', () => {
	it('gives the widest breakpoint the layout every item stores', () => {
		const items = [item(cell('a', 0, 0, 6, 2)), item(cell('b', 6, 0, 6, 2))]
		expect(placementsFor(items, BASE_BREAKPOINT.key)).toEqual([
			cell('a', 0, 0, 6, 2),
			cell('b', 6, 0, 6, 2),
		])
	})

	it('derives a breakpoint nobody arranged from the one above it', () => {
		const items = [item(cell('a', 0, 0, 6, 2)), item(cell('b', 6, 0, 6, 2))]
		expect(placementsFor(items, 'sm')).toEqual([
			cell('a', 0, 0, GRID_COLUMNS, 2),
			cell('b', 0, 2, GRID_COLUMNS, 2),
		])
	})

	it('gives an arranged item the placement it stores for that breakpoint', () => {
		const items = [
			item(cell('a', 0, 0, 6, 2), { sm: { x: 0, y: 0, w: 10, h: 4 } }),
			item(cell('b', 6, 0, 6, 2), { sm: { x: 10, y: 0, w: 10, h: 4 } }),
		]
		expect(placementsFor(items, 'sm')).toEqual([cell('a', 0, 0, 10, 4), cell('b', 10, 0, 10, 4)])
	})

	// A card added after the narrow layout was arranged has nothing stored for
	// it. It is placed below the arranged cells rather than on top of one.
	it('drops an item nobody arranged clear of the ones somebody did', () => {
		const items = [
			item(cell('a', 0, 0, 6, 2), { sm: { x: 0, y: 0, w: 20, h: 4 } }),
			item(cell('added', 6, 0, 6, 2)),
		]
		const placed = placementsFor(items, 'sm')
		expect(placed[0]).toEqual(cell('a', 0, 0, 20, 4))
		expect(placed[1].y).toBeGreaterThanOrEqual(4)
	})

	it('answers in the order the items came in, whatever the layout says', () => {
		const items = [item(cell('below', 0, 4, 6, 2)), item(cell('above', 0, 0, 6, 2))]
		expect(placementsFor(items, 'sm').map((layout) => layout.i)).toEqual(['below', 'above'])
	})
})

describe('writePlacement', () => {
	it('writes the widest breakpoint where every reader already looks', () => {
		const target = item(cell('a', 0, 0, 6, 2))
		writePlacement(target, BASE_BREAKPOINT.key, cell('a', 2, 3, 8, 4))
		expect(target.layout).toEqual(cell('a', 2, 3, 8, 4))
		expect(target.layouts).toEqual({})
	})

	it('writes a narrower breakpoint under its key, identity left behind', () => {
		const target = item(cell('a', 0, 0, 6, 2))
		writePlacement(target, 'sm', cell('a', 0, 6, 20, 3))
		expect(target.layouts?.sm).toEqual({ x: 0, y: 6, w: 20, h: 3 })
		expect(target.layout).toEqual(cell('a', 0, 0, 6, 2))
	})

	it('leaves the breakpoints it was not asked about alone', () => {
		const target = item(cell('a', 0, 0, 6, 2), { sm: { x: 0, y: 0, w: 20, h: 2 } })
		writePlacement(target, BASE_BREAKPOINT.key, cell('a', 4, 4, 6, 2))
		expect(target.layouts?.sm).toEqual({ x: 0, y: 0, w: 20, h: 2 })
	})
})
