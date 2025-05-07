<template>
	<grid-layout
		v-model:layout="layouts"
		v-bind="options"
		@layout-ready="() => (layoutReady = true)"
	>
		<template #default="{ gridItemProps }">
			<grid-item
				v-for="(layout, index) in layouts"
				v-bind="gridItemProps"
				:key="layout.i"
				:i="layout.i"
				:x="layout.x"
				:y="layout.y"
				:w="layout.w"
				:h="layout.h"
			>
				<slot
					v-if="layoutReady"
					name="item"
					:index="index"
					:i="layout.i"
					:x="layout.x"
					:y="layout.y"
					:w="layout.w"
					:h="layout.h"
				>
					<pre class="h-full w-full rounded bg-white p-4 shadow">
						{{ { i: layout.i, x: layout.x, y: layout.y, w: layout.w, h: layout.h } }}
					</pre
					>
				</slot>
			</grid-item>
		</template>
	</grid-layout>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

type Layout = {
	i: string
	x: number
	y: number
	w: number
	h: number
}
const layouts = defineModel<Layout[]>()
const layoutReady = ref(false)
const props = defineProps<{
	cols?: number
	disabled?: Boolean
}>()
const options = reactive({
	colNum: props.cols || 12,
	margin: [0, 0],
	rowHeight: 52,
	isDraggable: computed(() => !props.disabled),
	isResizable: computed(() => !props.disabled),
	responsive: true,
	verticalCompact: true,
	preventCollision: false,
	useCssTransforms: true,
	cols: {
		lg: props.cols || 12,
		md: props.cols || 12,
		sm: props.cols || 12,
		xs: 1,
		xxs: 1,
	},
})
</script>

<style lang="scss">
.vgl-layout {
	--vgl-placeholder-bg: #b1b1b1;
	--vgl-placeholder-opacity: 15%;
	--vgl-placeholder-z-index: 2;

	--vgl-item-resizing-z-index: 3;
	--vgl-item-resizing-opacity: 100%;
	--vgl-item-dragging-z-index: 3;
	--vgl-item-dragging-opacity: 100%;

	--vgl-resizer-size: 10px;
	--vgl-resizer-border-color: #444;
	--vgl-resizer-border-width: 2px;
}

.vgl-item--placeholder {
	z-index: var(--vgl-placeholder-z-index, 2);
	user-select: none;
	background-color: var(--vgl-placeholder-bg);
	opacity: var(--vgl-placeholder-opacity);
	transition-duration: 100ms;
	border-radius: 0.5rem;
}

.vgl-item__resizer {
	position: absolute;
	right: 12px;
	bottom: 12px;
	box-sizing: border-box;
	width: var(--vgl-resizer-size);
	height: var(--vgl-resizer-size);
	cursor: se-resize;
}

.vgl-item__resizer:before {
	position: absolute;
	inset: 0 3px 3px 0;
	content: '';
	border: 0 solid var(--vgl-resizer-border-color);
	border-right-width: var(--vgl-resizer-border-width);
	border-bottom-width: var(--vgl-resizer-border-width);
}
</style>
