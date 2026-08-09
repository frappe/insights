import { describe, expect, it } from 'vitest'
import {
	compactLayouts,
	placeGrid,
	resolveLayouts,
	stackLayouts,
	type GridLayoutItem,
} from './grid_placement'

// A cell, named so a case reads as the grid it describes.
function cell(i: string, x: number, y: number, w: number, h: number): GridLayoutItem {
	return { i, x, y, w, h }
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
		const stacked = stackLayouts([cell('a', 0, 0, 6, 2), cell('b', 6, 0, 6, 3)])
		expect(stacked).toEqual([cell('a', 0, 0, 1, 2), cell('b', 0, 2, 1, 3)])
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
		const placed = placeGrid([cell('a', 0, 0, 6, 2), cell('b', 6, 0, 6, 2)], {
			columns: 12,
			width: WIDE,
		})
		expect(Object.keys(placed.cells).sort()).toEqual(['a', 'b'])
	})

	it('collapses to one column on a narrow grid', () => {
		const placed = placeGrid([cell('a', 0, 0, 6, 2), cell('b', 6, 0, 6, 2)], {
			columns: 12,
			width: NARROW,
		})
		expect(placed.columns).toBe(1)
		expect(placed.cells.b).toEqual(cell('b', 0, 2, 1, 2))
	})

	it('keeps its columns on a wide grid', () => {
		const placed = placeGrid([cell('a', 0, 0, 6, 2)], { columns: 12, width: WIDE })
		expect(placed.columns).toBe(12)
	})

	it('closes the gaps when the dashboard asks for compaction', () => {
		const placed = placeGrid([cell('a', 0, 7, 6, 2)], {
			columns: 12,
			width: WIDE,
			verticalCompact: true,
		})
		expect(placed.cells.a.y).toBe(0)
	})

	it('leaves the gaps where the dashboard does not', () => {
		const placed = placeGrid([cell('a', 0, 7, 6, 2)], {
			columns: 12,
			width: WIDE,
			verticalCompact: false,
		})
		expect(placed.cells.a.y).toBe(7)
	})

	// The grid reports zero before it has been measured. Collapsing then would
	// draw one column for a frame and reflow, which reads as the page breaking.
	it('draws its columns before the grid has been measured', () => {
		const placed = placeGrid([cell('a', 0, 0, 6, 2)], { columns: 12, width: 0 })
		expect(placed.columns).toBe(12)
	})
})
