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
							class="h-5 w-5 rounded-sm"
							:class="selectedPalette.value === 'custom' ? 'cursor-pointer' : ''"
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

<script setup>
import { generateColorPalette, getColors } from '@/utils/colors'
import { Plus } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import ColorPicker from './ColorPicker.vue'

const colorPaletteOptions = [
	{ label: 'Default', value: 'default' },
	{ label: 'Blues', value: 'blue' },
	{ label: 'Greens', value: 'green' },
	{ label: 'Yellows', value: 'yellow' },
	{ label: 'Teals', value: 'teal' },
	{ label: 'Custom', value: 'custom' },
]
const paletteColors = colorPaletteOptions.reduce((acc, option) => {
	if (option.value !== 'custom') {
		acc[option.value] = generateColorPalette(option.value)
	}
	if (option.value === 'default') {
		acc[option.value] = getColors().slice(0, 10)
	}
	return acc
}, {})

const selectedPalette = ref()
watch(selectedPalette, () => (colors.value = selectedPaletteColors.value))
const selectedPaletteColors = computed(() => getPaletteColors(selectedPalette.value.value))

const colors = defineModel()
if (!colors.value?.length) {
	selectedPalette.value = colorPaletteOptions.at(0)
} else if (isCustomPalette(colors.value)) {
	selectedPalette.value = colorPaletteOptions.at(-1)
} else {
	selectedPalette.value = guessPredefinedPalette(colors.value)
}

function getPaletteColors(palette) {
	if (palette === 'custom') {
		return colors.value?.length ? colors.value : getPaletteColors('default')
	}
	return paletteColors[palette] ?? []
}

function guessPredefinedPalette(colors) {
	if (!colors?.length) return false
	return colorPaletteOptions.find((palette) =>
		colors.every((color) => paletteColors[palette.value]?.includes(color))
	)
}
function isCustomPalette(colors) {
	const isPredefinedPalette = guessPredefinedPalette(colors)
	return !isPredefinedPalette && colors.length > 0
}

function handleColorChange(color, index) {
	if (selectedPalette.value.value !== 'custom') {
		selectedPalette.value = colorPaletteOptions[1]
		colors.value = selectedPaletteColors.value.length
			? selectedPaletteColors.value
			: getPaletteColors('default')
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
