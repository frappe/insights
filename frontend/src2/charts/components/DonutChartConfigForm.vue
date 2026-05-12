<script setup lang="ts">
import { computed, ref, watch, watchEffect } from 'vue'
import { __ } from '../../translation'
import { FIELDTYPES } from '../../helpers/constants'
import { DonutChartConfig } from '../../types/chart.types'
import { ColumnOption, Dimension, DimensionOption, Measure } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import DimensionPicker from './DimensionPicker.vue'
import MeasurePicker from './MeasurePicker.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	columnOptions: ColumnOption[]
}>()

const config = defineModel<DonutChartConfig>({
	required: true,
	default: () => ({
		label_column: {},
		value_column: {},
		label_colors: [],
	}),
})

watchEffect(() => {
	if (!config.value.label_column) config.value.label_column = {} as Dimension
	if (!config.value.value_column) config.value.value_column = {} as Measure
	if (!config.value.label_colors) config.value.label_colors = []
})

const discrete_dimensions = computed(() =>
	props.dimensions.filter((d) => FIELDTYPES.DISCRETE.includes(d.data_type)),
)

const colorPalettes = [
	{
		label: 'Default',
		value: 'default',
		colors: ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de'],
	},
	{
		label: 'Blues',
		value: 'blue',
		colors: ['#03045E', '#023E8A', '#0077B6', '#00B4D8', '#90E0EF'],
	},
	{
		label: 'Greens',
		value: 'green',
		colors: ['#1B4332', '#2D6A4F', '#40916C', '#74C69D', '#B7E4C7'],
	},
	{
		label: 'Yellows',
		value: 'yellow',
		colors: ['#FF6700', '#FF8500', '#FFA200', '#FFC300', '#FFD60A'],
	},
	{
		label: 'Teals',
		value: 'teal',
		colors: ['#004F52', '#00787A', '#00A896', '#02C39A', '#6FEDD6'],
	},
	{ label: 'Custom', value: 'custom', colors: [] },
]

const FULL_PALETTE: string[] = [
	'#fff5f5',
	'#ffe3e3',
	'#ffc9c9',
	'#ffa8a8',
	'#ff8787',
	'#ff6b6b',
	'#fa5252',
	'#f03e3e',
	'#e03131',
	'#c92a2a',
	'#fff0f6',
	'#ffdeeb',
	'#fcc2d7',
	'#faa2c1',
	'#f783ac',
	'#f06595',
	'#e64980',
	'#d6336c',
	'#c2255c',
	'#a61e4d',
	'#f8f0fc',
	'#f3d9fa',
	'#eebefa',
	'#e599f7',
	'#da77f2',
	'#cc5de8',
	'#be4bdb',
	'#ae3ec9',
	'#9c36b5',
	'#862e9c',
	'#f3f0ff',
	'#e5dbff',
	'#d0bfff',
	'#b197fc',
	'#9775fa',
	'#845ef7',
	'#7950f2',
	'#7048e8',
	'#6741d9',
	'#5f3dc4',
	'#e8f4fd',
	'#d0ebff',
	'#a5d8ff',
	'#74c0fc',
	'#4dabf7',
	'#339af0',
	'#228be6',
	'#1c7ed6',
	'#1971c2',
	'#1864ab',
	'#e3fafc',
	'#c5f6fa',
	'#99e9f2',
	'#66d9e8',
	'#3bc9db',
	'#22b8cf',
	'#15aabf',
	'#1098ad',
	'#0c8599',
	'#0b7285',
	'#e6fcf5',
	'#c3fae8',
	'#96f2d7',
	'#63e6be',
	'#38d9a9',
	'#20c997',
	'#12b886',
	'#0ca678',
	'#099268',
	'#087f5b',
	'#ebfbee',
	'#d3f9d8',
	'#b2f2bb',
	'#8ce99a',
	'#69db7c',
	'#51cf66',
	'#40c057',
	'#37b24d',
	'#2f9e44',
	'#2b8a3e',
	'#f4fce3',
	'#e9fac8',
	'#d8f5a2',
	'#c0eb75',
	'#a9e34b',
	'#94d82d',
	'#82c91e',
	'#74b816',
	'#66a80f',
	'#5c940d',
	'#fff9db',
	'#fff3bf',
	'#ffec99',
	'#ffe066',
	'#ffd43b',
	'#fcc419',
	'#fab005',
	'#f59f00',
	'#f08c00',
	'#e67700',
	'#fff4e6',
	'#ffe8cc',
	'#ffd8a8',
	'#ffc078',
	'#ffa94d',
	'#ff922b',
	'#fd7e14',
	'#f76707',
	'#e8590c',
	'#d9480f',
	'#f8f9fa',
	'#f1f3f5',
	'#e9ecef',
	'#dee2e6',
	'#ced4da',
	'#adb5bd',
	'#868e96',
	'#495057',
	'#343a40',
	'#212529',
]

const paletteOptions = computed(() =>
	colorPalettes.map((p) => ({
		label: p.label,
		value: p.value,
		colors: p.value === 'custom' ? [] : p.colors,
	})),
)

function getPaletteColors(value: string): string[] {
	if (value === 'custom') {
		return config.value.label_colors?.length
			? [...config.value.label_colors]
			: [...colorPalettes[0].colors]
	}
	return [...(colorPalettes.find((p) => p.value === value)?.colors ?? [])]
}

function guessPalette(colors: string[]): string {
	if (!colors?.length) return 'default'
	const match = colorPalettes.find(
		(p) =>
			p.value !== 'custom' &&
			colors.length === p.colors.length &&
			colors.every((c, i) => c === p.colors[i]),
	)
	return match ? match.value : 'custom'
}

const selectedPaletteValue = ref<string>(
	config.value.label_colors?.length ? guessPalette(config.value.label_colors) : 'default',
)

const selectedPaletteOption = computed({
	get() {
		return paletteOptions.value.find((o) => o.value === selectedPaletteValue.value) ?? null
	},
	set(opt: { label: string; value: string } | null) {
		if (!opt) return
		selectedPaletteValue.value = opt.value
	},
})

watch(selectedPaletteValue, (val) => {
	if (val !== 'custom') {
		config.value.label_colors = getPaletteColors(val)
	}
})

const displayedColors = computed<string[]>(() => getPaletteColors(selectedPaletteValue.value))

const editingIdx = ref<number | null>(null)

function openPicker(idx: number) {
	if (selectedPaletteValue.value !== 'custom') return
	editingIdx.value = editingIdx.value === idx ? null : idx
}

function selectColor(color: string) {
	if (editingIdx.value === null) return
	if (selectedPaletteValue.value !== 'custom') {
		config.value.label_colors = [...displayedColors.value]
		selectedPaletteValue.value = 'custom'
	}
	const updated = [...(config.value.label_colors ?? [])]
	updated[editingIdx.value] = color
	config.value.label_colors = updated
	editingIdx.value = null
}

function handleNativeColorInput(e: Event, idx: number) {
	const newColor = (e.target as HTMLInputElement).value
	if (selectedPaletteValue.value !== 'custom') {
		config.value.label_colors = [...displayedColors.value]
		selectedPaletteValue.value = 'custom'
	}
	const updated = [...(config.value.label_colors ?? [])]
	updated[idx] = newColor
	config.value.label_colors = updated
}

function closePicker() {
	editingIdx.value = null
}
</script>

<template>
	<CollapsibleSection title="Options">
		<div class="flex flex-col gap-3 pt-1">
			<DimensionPicker
				label="Label"
				v-model="config.label_column"
				:options="discrete_dimensions"
			/>

			<div class="flex flex-col gap-1.5">
				<span class="text-sm text-gray-600">{{ __('Color Palette') }}</span>

				<Autocomplete
					v-model="selectedPaletteOption"
					:options="paletteOptions"
					:placeholder="__('Select palette')"
				>
					<template #item-prefix="{ option }">
						<span class="mr-1.5 flex items-center gap-0.5">
							<template v-if="option.colors?.length">
								<span
									v-for="color in option.colors.slice(0, 5)"
									:key="color"
									class="inline-block h-3 w-3 rounded-full"
									:style="{ backgroundColor: color }"
								/>
							</template>
							<template v-else>
								<span
									class="inline-block h-3 w-3 rounded-full border border-dashed border-gray-400"
								/>
							</template>
						</span>
					</template>
				</Autocomplete>

				<div class="flex flex-wrap gap-1 px-0.5 pt-0.5">
					<div v-for="(color, idx) in displayedColors" :key="idx" class="relative">
						<button
							type="button"
							class="block h-5 w-5 rounded-sm border transition-all"
							:class="[
								selectedPaletteValue === 'custom'
									? 'cursor-pointer hover:scale-110 hover:shadow-md'
									: 'cursor-default',
								editingIdx === idx
									? 'border-gray-700 ring-2 ring-gray-400 ring-offset-1'
									: 'border-gray-200',
							]"
							:style="{ backgroundColor: color }"
							:title="
								selectedPaletteValue === 'custom'
									? __('Click to edit color')
									: color
							"
							@click="openPicker(idx)"
						/>
					</div>
				</div>

				<Transition
					enter-active-class="transition-all duration-150 ease-out"
					enter-from-class="opacity-0 -translate-y-1"
					enter-to-class="opacity-100 translate-y-0"
					leave-active-class="transition-all duration-100 ease-in"
					leave-from-class="opacity-100 translate-y-0"
					leave-to-class="opacity-0 -translate-y-1"
				>
					<div
						v-if="selectedPaletteValue === 'custom' && editingIdx !== null"
						class="rounded-md border border-gray-200 bg-white p-2 shadow-md"
					>
						<div class="mb-1.5 flex items-center justify-between">
							<span class="text-xs text-gray-500">
								{{ __('Pick a color for slot') }} {{ (editingIdx ?? 0) + 1 }}
							</span>
							<button
								type="button"
								class="text-xs text-gray-400 hover:text-gray-600"
								@click="closePicker"
							>
								✕
							</button>
						</div>

						<div
							class="grid gap-0.5"
							style="grid-template-columns: repeat(10, minmax(0, 1fr))"
						>
							<button
								v-for="swatch in FULL_PALETTE"
								:key="swatch"
								type="button"
								class="h-4 w-4 rounded-sm transition-transform hover:scale-125 hover:shadow-sm focus:outline-none focus:ring-1 focus:ring-gray-400"
								:style="{ backgroundColor: swatch }"
								:title="swatch"
								@click="selectColor(swatch)"
							/>
						</div>

						<div class="mt-2 flex items-center gap-2 border-t border-gray-100 pt-2">
							<span class="text-xs text-gray-400">{{ __('Custom hex') }}</span>
							<div class="relative flex items-center gap-1.5">
								<span
									class="h-4 w-4 rounded-sm border border-gray-200"
									:style="{
										backgroundColor:
											editingIdx !== null
												? config.label_colors?.[editingIdx] ??
												  displayedColors[editingIdx]
												: '#ffffff',
									}"
								/>
								<input
									type="color"
									:value="
										editingIdx !== null
											? config.label_colors?.[editingIdx] ??
											  displayedColors[editingIdx]
											: '#ffffff'
									"
									class="h-5 w-16 cursor-pointer rounded border border-gray-200 bg-transparent p-0 text-xs"
									@input="
										(e) => {
											if (editingIdx !== null)
												handleNativeColorInput(e, editingIdx)
										}
									"
								/>
							</div>
						</div>
					</div>
				</Transition>
			</div>

			<MeasurePicker
				label="Value"
				v-model="config.value_column"
				:column-options="props.columnOptions"
			/>
			<FormControl
				v-if="!config.show_inline_labels"
				v-model="config.legend_position"
				label="Legend Position"
				type="select"
				:options="[
					{ label: __('Top'), value: 'top' },
					{ label: __('Bottom'), value: 'bottom' },
					{ label: __('Left'), value: 'left' },
					{ label: __('Right'), value: 'right' },
				]"
			/>
			<FormControl v-model="config.max_slices" label="Max Slices" type="number" min="1" />
			<Toggle v-model="config.show_inline_labels" label="Inline Labels" />
		</div>
	</CollapsibleSection>
</template>
