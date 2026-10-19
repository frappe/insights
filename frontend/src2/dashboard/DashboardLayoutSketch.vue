<script setup lang="ts">
import { computed } from 'vue'
import { GRID_COLUMNS } from './grid_placement'
import type { DashboardCell } from './dashboards'

// The top of a dashboard's layout, each card drawn as a wireframe of what it
// shows, for a dashboard that has no preview image.
const props = defineProps<{ cells: DashboardCell[] }>()

const COLUMN = 10
const ROW = 4.2
const GAP = 1.2
const PAD = 3
const WIDTH = GRID_COLUMNS * COLUMN + PAD * 2
// as tall as wide, so the sketch always fills the card's width and the card crops its foot
const HEIGHT = WIDTH
// the first screen of a dashboard: its filters, numbers and first row of charts
const ROWS = 20

type Shape =
	| { type: 'rect'; x: number; y: number; width: number; height: number; rx: number }
	| { type: 'polyline'; points: string }
	| { type: 'ring'; cx: number; cy: number; r: number }

const BAR_HEIGHTS = [0.5, 0.75, 0.6, 0.95, 0.7, 0.85]
const ROW_WIDTHS = [0.9, 0.7, 0.55, 0.4]
const LINE_YS = [0.75, 0.5, 0.6, 0.3, 0.4, 0.15]

function line(x: number, y: number, width: number, height: number): Shape {
	return { type: 'rect', x, y, width, height, rx: Math.min(height / 2, 1) }
}

function glyph(kind: string, x: number, y: number, w: number, h: number): Shape[] {
	const ix = x + w * 0.14
	const iw = w * 0.72
	const iy = y + h * 0.24
	const ih = h * 0.56
	switch (kind) {
		case 'filter':
		case 'text':
			return [line(x + 2, y + h / 2 - 0.6, Math.min(w * 0.4, 12), 1.2)]
		case 'Number':
			return [line(x + 2.2, y + h / 2 - 0.9, w * 0.45, 1.8)]
		case 'Bar': {
			const n = Math.max(3, Math.min(BAR_HEIGHTS.length, Math.round(w / 6)))
			const slot = iw / n
			return Array.from({ length: n }, (_, i) => {
				const height = ih * BAR_HEIGHTS[i]
				const width = Math.min(slot * 0.5, 4)
				return line(ix + i * slot + (slot - width) / 2, iy + ih - height, width, height)
			})
		}
		case 'Row': {
			const n = ROW_WIDTHS.length
			return ROW_WIDTHS.map((width, i) =>
				line(ix, iy + (i * ih) / n, iw * width, Math.min((ih / n) * 0.45, 2.4)),
			)
		}
		case 'Line':
			return [
				{
					type: 'polyline',
					points: LINE_YS.map(
						(v, i) => `${ix + (i * iw) / (LINE_YS.length - 1)},${iy + ih * v}`,
					).join(' '),
				},
			]
		case 'Table': {
			const n = 4
			return Array.from({ length: n }, (_, i) => line(ix, iy + (i * ih) / n, iw, 1.1))
		}
		case 'Funnel': {
			const n = ROW_WIDTHS.length
			return ROW_WIDTHS.map((width, i) =>
				line(x + (w - iw * width) / 2, iy + (i * ih) / n, iw * width, (ih / n) * 0.6),
			)
		}
		case 'Donut':
			return [{ type: 'ring', cx: x + w / 2, cy: y + h / 2, r: Math.min(w, h) * 0.26 }]
		default:
			return [line(ix, iy, iw, ih)]
	}
}

const cards = computed(() =>
	props.cells
		.filter((cell) => cell.y < ROWS)
		.map((cell) => {
			const x = PAD + cell.x * COLUMN + GAP / 2
			const y = PAD + cell.y * ROW + GAP / 2
			const w = cell.w * COLUMN - GAP
			const h = cell.h * ROW - GAP
			return { x, y, w, h, shapes: glyph(cell.kind, x, y, w, h) }
		}),
)
</script>

<template>
	<svg
		class="h-full w-full bg-surface-gray-1"
		:viewBox="`0 0 ${WIDTH} ${HEIGHT}`"
		preserveAspectRatio="xMidYMin slice"
		aria-hidden="true"
	>
		<g v-for="(card, index) in cards" :key="index">
			<rect
				:x="card.x"
				:y="card.y"
				:width="card.w"
				:height="card.h"
				rx="2"
				class="fill-surface-base"
			/>
			<template v-for="(shape, i) in card.shapes" :key="i">
				<rect
					v-if="shape.type === 'rect'"
					:x="shape.x"
					:y="shape.y"
					:width="shape.width"
					:height="shape.height"
					:rx="shape.rx"
					class="fill-ink-gray-2"
				/>
				<polyline
					v-else-if="shape.type === 'polyline'"
					:points="shape.points"
					fill="none"
					stroke-width="0.8"
					stroke-linejoin="round"
					stroke-linecap="round"
					class="stroke-ink-gray-2"
				/>
				<circle
					v-else
					:cx="shape.cx"
					:cy="shape.cy"
					:r="shape.r"
					fill="none"
					:stroke-width="shape.r * 0.3"
					class="stroke-ink-gray-2"
				/>
			</template>
		</g>
	</svg>
</template>
