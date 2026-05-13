<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps<{ modelValue?: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

interface Palette {
	label: string
	color: string
	swatch: string
}

const PALETTES: Palette[] = [
	{ label: 'Default', color: '#000000', swatch: '#111827' },
	{ label: 'Blues', color: '#1D4ED8', swatch: '#1D4ED8' },
	{ label: 'Greens', color: '#15803D', swatch: '#15803D' },
	{ label: 'Yellows', color: '#B45309', swatch: '#B45309' },
	{ label: 'Teals', color: '#0F766E', swatch: '#0F766E' },
]

const isOpen = ref(false)
const search = ref('')
const customColor = ref(props.modelValue ?? '#000000')
const triggerRef = ref<HTMLElement | null>(null)
const dropdownStyle = ref<Record<string, string>>({})

function matchPalette(hex?: string): Palette | null {
	if (!hex) return PALETTES[0]
	return PALETTES.find((p) => p.color.toLowerCase() === hex.toLowerCase()) ?? null
}

const selected = ref<Palette | null>(matchPalette(props.modelValue))
const isCustom = ref(selected.value === null && !!props.modelValue)

watch(
	() => props.modelValue,
	(v) => {
		const match = matchPalette(v)
		if (match) {
			selected.value = match
			isCustom.value = false
		} else {
			selected.value = null
			isCustom.value = true
			customColor.value = v ?? '#000000'
		}
	},
)

const filtered = computed(() =>
	PALETTES.filter((p) => p.label.toLowerCase().includes(search.value.toLowerCase())),
)

const displayLabel = computed(() => {
	if (isCustom.value) return 'Custom'
	return selected.value?.label ?? 'Default'
})

const displaySwatch = computed(() => {
	if (isCustom.value) return customColor.value
	return selected.value?.swatch ?? '#111827'
})

function selectPalette(palette: Palette) {
	selected.value = palette
	isCustom.value = false
	isOpen.value = false
	search.value = ''
	emit('update:modelValue', palette.color)
}

function selectCustom() {
	selected.value = null
	isCustom.value = true
	isOpen.value = false
	search.value = ''
	emit('update:modelValue', customColor.value)
}

function onCustomColorChange(e: Event) {
	const hex = (e.target as HTMLInputElement).value
	customColor.value = hex
	emit('update:modelValue', hex)
}

async function toggleOpen() {
	isOpen.value = !isOpen.value
	if (!isOpen.value) {
		search.value = ''
		return
	}
	await nextTick()
	const rect = triggerRef.value?.getBoundingClientRect()
	if (rect) {
		dropdownStyle.value = {
			position: 'fixed',
			top: `${rect.bottom + 4}px`,
			left: `${rect.left}px`,
			width: `${rect.width}px`,
			zIndex: '9999',
		}
	}
}

function closeDropdown() {
	isOpen.value = false
	search.value = ''
}
</script>

<template>
	<div class="relative w-full" v-click-outside="closeDropdown">
		<button
			ref="triggerRef"
			type="button"
			class="flex w-full items-center justify-between rounded border border-gray-300 bg-white px-2.5 py-1.5 text-sm shadow-sm hover:bg-gray-50 focus:outline-none"
			@click="toggleOpen"
		>
			<div class="flex items-center gap-2">
				<span
					class="inline-block h-3.5 w-3.5 rounded-sm border border-gray-300"
					:style="{ background: displaySwatch }"
				/>
				<span class="text-gray-800">{{ displayLabel }}</span>
			</div>
			<svg
				class="h-4 w-4 text-gray-500 transition-transform"
				:class="{ 'rotate-180': isOpen }"
				viewBox="0 0 20 20"
				fill="currentColor"
			>
				<path
					fill-rule="evenodd"
					d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
					clip-rule="evenodd"
				/>
			</svg>
		</button>

		<Teleport to="body">
			<Transition
				enter-active-class="transition duration-100 ease-out"
				enter-from-class="opacity-0 scale-95"
				enter-to-class="opacity-100 scale-100"
				leave-active-class="transition duration-75 ease-in"
				leave-from-class="opacity-100 scale-100"
				leave-to-class="opacity-0 scale-95"
			>
				<div
					v-if="isOpen"
					:style="dropdownStyle"
					class="origin-top-left rounded-md border border-gray-200 bg-white shadow-lg"
				>
					<div class="p-1.5">
						<div
							class="flex items-center rounded border border-gray-300 bg-gray-50 px-2 py-1"
						>
							<svg
								class="mr-1.5 h-3.5 w-3.5 flex-shrink-0 text-gray-400"
								viewBox="0 0 20 20"
								fill="currentColor"
							>
								<path
									fill-rule="evenodd"
									d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
									clip-rule="evenodd"
								/>
							</svg>
							<input
								v-model="search"
								type="text"
								placeholder="Search"
								class="w-full bg-transparent text-sm text-gray-700 placeholder-gray-400 outline-none"
							/>
							<button
								v-if="search"
								@click="search = ''"
								class="ml-1 text-gray-400 hover:text-gray-600"
							>
								<svg class="h-3.5 w-3.5" viewBox="0 0 20 20" fill="currentColor">
									<path
										d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
									/>
								</svg>
							</button>
						</div>
					</div>

					<ul class="max-h-48 overflow-y-auto py-0.5">
						<li
							v-for="palette in filtered"
							:key="palette.label"
							class="flex cursor-pointer items-center gap-2.5 px-3 py-2 text-sm hover:bg-gray-100"
							:class="{
								'bg-gray-100 font-medium':
									selected?.label === palette.label && !isCustom,
							}"
							@click="selectPalette(palette)"
						>
							<span
								class="inline-block h-3 w-3 rounded-sm border border-gray-300"
								:style="{ background: palette.swatch }"
							/>
							{{ palette.label }}
						</li>

						<li
							v-if="!search || 'custom'.includes(search.toLowerCase())"
							class="flex cursor-pointer items-center gap-2.5 px-3 py-2 text-sm hover:bg-gray-100"
							:class="{ 'bg-gray-100 font-medium': isCustom }"
							@click="selectCustom"
						>
							<span
								class="inline-block h-3 w-3 rounded-sm border border-gray-300"
								:style="{ background: customColor }"
							/>
							Custom
						</li>
					</ul>
				</div>
			</Transition>
		</Teleport>

		<div v-if="isCustom" class="mt-2 flex items-center gap-2">
			<input
				type="color"
				:value="customColor"
				@input="onCustomColorChange"
				class="h-7 w-10 cursor-pointer rounded border border-gray-300 bg-white p-0.5"
			/>
			<span class="text-xs text-gray-500">{{ customColor }}</span>
		</div>
	</div>
</template>
