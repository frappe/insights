<template>
	<grid-layout v-model:layout="items" v-bind="options" :key="refreshID">
		<template #default="{ gridItemProps }">
			<grid-item
				v-for="item in items"
				v-bind="gridItemProps"
				:key="item.i"
				:i="item.i"
				:x="item.x"
				:y="item.y"
				:w="item.w"
				:h="item.h"
			>
				<slot name="item" v-bind="{ item }"> {{ item.i }}</slot>
			</grid-item>
		</template>
	</grid-layout>
</template>

<script setup>
import { debounce } from 'frappe-ui'
import { computed, defineExpose, reactive, ref, watch } from 'vue'

const props = defineProps({
	items: { type: Array, required: true },
	disabled: { type: Boolean, default: false },
})
const options = reactive({
	colNum: 20,
	margin: [8, 8],
	rowHeight: 22,
	isDraggable: false,
	isResizable: false,
	responsive: true,
	verticalCompact: false,
	preventCollision: true,
	useCssTransforms: true,
	cols: { lg: 20, md: 20, sm: 8, xs: 1, xxs: 1 },
})
const items = ref(props.items)
watch(
	() => props.items,
	(val) => (items.value = val),
	{ deep: true }
)
const layouts = computed(() => {
	return items.value.map((item) => {
		return {
			i: item.i,
			x: item.x,
			y: item.y,
			w: item.w,
			h: item.h,
		}
	})
})
defineExpose({ layouts, refresh })

const refreshID = ref(0)
async function toggleEnable(disable) {
	if (options.isDraggable === !disable && options.isResizable === !disable) return
	refreshID.value++
	options.isDraggable = !disable
	options.isResizable = !disable
	await nextTick()
}
watch(() => props.disabled, debounce(toggleEnable, 200))

function refresh() {
	refreshID.value++
}

window.gridOptions = options
window.refreshGrid = refresh
</script>

<style>
.vue-grid-item .resizing {
	opacity: 0.8;
}

.vue-grid-item {
	border-radius: 0.375rem;
	background: none;
}

.vue-grid-item.vue-grid-placeholder {
	background: #818181;
	opacity: 0.2;
	transition-duration: 0.1s;
}

.vue-grid-item > .vue-resizable-handle {
	position: absolute;
	width: 20px;
	height: 20px;
	z-index: 20;
	bottom: 0;
	right: 0;
	background-image: url(data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBzdGFuZGFsb25lPSJubyI/Pg08c3ZnIGlkPSJVbnRpdGxlZC1QYWdlJTIwMSIgdmlld0JveD0iMCAwIDYgNiIgc3R5bGU9ImJhY2tncm91bmQtY29sb3I6I2ZmZmZmZjAwIiB2ZXJzaW9uPSIxLjEiDQl4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHhtbG5zOnhsaW5rPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5L3hsaW5rIiB4bWw6c3BhY2U9InByZXNlcnZlIg0JeD0iMHB4IiB5PSIwcHgiIHdpZHRoPSI2cHgiIGhlaWdodD0iNnB4Ig0+DQk8ZyBvcGFjaXR5PSIwLjMwMiI+DQkJPHBhdGggZD0iTSA2IDYgTCAwIDYgTCAwIDQuMiBMIDQgNC4yIEwgNC4yIDQuMiBMIDQuMiAwIEwgNiAwIEwgNiA2IEwgNiA2IFoiIGZpbGw9IiMwMDAwMDAiLz4NCTwvZz4NPC9zdmc+);
	background-position: bottom right;
	background-size: 8px;
	background-repeat: no-repeat;
	padding: 0 3px 3px 0;
	background-origin: content-box;
	box-sizing: border-box;
	cursor: se-resize;
}
</style>
