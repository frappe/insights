<script setup>
import Checkbox from '@/components/Controls/Checkbox.vue'
import ColorInput from '@/components/Controls/ColorInput.vue'
import Tabs from '@/components/Tabs.vue'
import UsePopover from '@/components/UsePopover.vue'
import { computed, ref } from 'vue'

const emit = defineEmits(['update:modelValue', 'remove'])
const props = defineProps({
	modelValue: { required: true },
	seriesType: { type: String },
})
const series = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})
if (props.seriesType) {
	series.value.type = props.seriesType
}
if (!series.value.column) {
	series.value.column = {}
}
if (!series.value.type) {
	series.value.type = 'bar'
}

const menuAnchor = ref(null)
const showMenu = ref(false)
function onRemove() {
	emit('remove')
	showMenu.value = false
}
</script>

<template>
	<div class="-m-1 flex flex-1 items-center space-x-2 overflow-hidden p-1">
		<div class="h-7 w-full flex-1 truncate rounded bg-gray-100 py-1 px-2 leading-5">
			{{ series.column }}
		</div>
		<div ref="menuAnchor" class="flex-shrink-0">
			<Button icon="more-horizontal" variant="subtle" @click="showMenu = !showMenu" />
			<UsePopover
				v-if="menuAnchor"
				:show="showMenu"
				:targetElement="menuAnchor"
				placement="right-start"
			>
				<div
					class="h-fit max-h-[16rem] w-[15rem] space-y-3 overflow-y-scroll rounded bg-white p-3 text-base shadow"
				>
					<p class="text-gray-700">Series Options</p>

					<div v-if="!props.seriesType">
						<span class="mb-1 block text-sm leading-4 text-gray-700"> Axis Type </span>
						<Tabs
							v-model="series.type"
							:tabs="[
								{ label: 'Line', value: 'line' },
								{ label: 'Bar', value: 'bar' },
							]"
						/>
					</div>

					<ColorInput label="Color" v-model="series.color" placement="right-start" />

					<template v-if="series.type == 'line'">
						<div class="space-y-2 text-gray-600">
							<Checkbox v-model="series.smoothLines" label="Enable Curved Lines" />
						</div>

						<div class="space-y-2 text-gray-600">
							<Checkbox v-model="series.showPoints" label="Show Data Points" />
						</div>

						<div class="space-y-2 text-gray-600">
							<Checkbox v-model="series.showArea" label="Show Area" />
						</div>
					</template>

					<div class="flex justify-end">
						<Button variant="ghost" @click="showMenu = false"> Close </Button>
						<Button variant="ghost" theme="red" @click="onRemove"> Remove </Button>
					</div>
				</div>
			</UsePopover>
		</div>
	</div>
</template>
