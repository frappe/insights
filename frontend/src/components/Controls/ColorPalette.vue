<template>
	<div>
		<label class="mb-1.5 block text-xs text-gray-600">Color Palette</label>
		<Autocomplete
			v-model="selectedPalette"
			:options="colorPaletteOptions"
			placeholder="Color palette"
		>
		</Autocomplete>
		<div class="mt-1.5 flex flex-wrap gap-1 px-1">
			<template
				v-for="(color, index) in getPaletteColors(selectedPalette.value)"
				:key="index"
			>
				<ColorPicker
					:modelValue="color"
					@update:modelValue="handleColorChange($event, index)"
				>
					<template #target="{ togglePopover }">
						<div
							class="h-5 w-5 cursor-pointer rounded-sm"
							:style="{ backgroundColor: color }"
							@click="togglePopover"
							@click.meta="removeColor(index)"
						></div>
					</template>
				</ColorPicker>
			</template>
			<ColorPicker
				:modelValue="newColor"
				@update:modelValue="handleColorChange($event, newColorIndex)"
			>
				<template #target="{ togglePopover }">
					<div
						class="flex h-5 w-5 cursor-pointer items-center justify-center rounded-sm border border-dashed border-gray-500 text-gray-500 hover:border-gray-700 hover:text-gray-700"
						@click="
							() => {
								togglePopover()
								newColor = '#000000'
								newColorIndex = getPaletteColors(selectedPalette.value).length
							}
						"
					>
						<Plus class="h-3 w-3" />
					</div>
				</template>
			</ColorPicker>
		</div>
	</div>
</template>
; ;;
<script setup>
import { getColors } from '@/utils/colors'
import { debounce } from 'frappe-ui'
import { Plus } from 'lucide-vue-next'
import { ref } from 'vue'
import ColorPicker from './ColorPicker.vue'

const colors = defineModel()

const paletteColors = {
	default: getColors().slice(0, 10),
}
const colorPaletteOptions = [
	{ label: 'Default', value: 'default' },
	{ label: 'Custom', value: 'custom' },
]
const selectedPalette = ref()
if (colors.value?.length === 0) {
	selectedPalette.value = colorPaletteOptions[0]
} else if (isDefaultPalette(colors.value)) {
	selectedPalette.value = colorPaletteOptions[0]
} else {
	selectedPalette.value = colorPaletteOptions[1]
}

function getPaletteColors(palette) {
	if (palette === 'custom') {
		return colors.value?.length ? colors.value : getPaletteColors('default')
	}
	return paletteColors[palette] ?? []
}
function isDefaultPalette(colors) {
	if (!colors) return true
	return colors.every((color, index) => color === paletteColors.default[index])
}

function handleColorChange(color, index) {
	if (selectedPalette.value.value !== 'custom') {
		const currentColors = [...getPaletteColors(selectedPalette.value.value)]
		selectedPalette.value = colorPaletteOptions[1]
		colors.value = currentColors.length ? currentColors : getPaletteColors('default')
	}
	colors.value[index] = color
}

const newColor = ref('#000000')
const newColorIndex = ref(0)

function removeColor(index) {
	if (selectedPalette.value.value !== 'custom') return
	colors.value.splice(index, 1)
}
</script>
