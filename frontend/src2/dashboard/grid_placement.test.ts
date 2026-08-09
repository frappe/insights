import { describe, expect, it } from 'vitest'
import { compactLayouts, placeGrid, stackLayouts, type GridLayoutItem } from './grid_placement'

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
		const stacked = stackLayouts([cell('right', 6, 0, 6, 2), cell('below', 0, 4, 12, 2), cell('left', 0, 0, 6, 2)])
		expect(stacked.map((item) => item.i)).toEqual(['left', 'right', 'below'])
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
