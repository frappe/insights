<script setup lang="ts">
import { TextInput } from 'frappe-ui'
import { computed, ref } from 'vue'
import {
	FILTER_ICON_GROUPS,
	filterIconClass,
	filterIconLabel,
	type FilterIconGroup,
} from './filter_icons'

// Picks the icon a filter wears. The list is short enough to read in a couple
// of scrolls, so search only narrows it — it never hides a glyph the way a
// full-pack picker hides its 1500th.
const icon = defineModel<string | undefined>()

const search = ref('')

const groups = computed<FilterIconGroup[]>(() => {
	const term = search.value.trim().toLowerCase()
	if (!term) return FILTER_ICON_GROUPS
	return FILTER_ICON_GROUPS.map((group) => ({
		label: group.label,
		icons: group.icons.filter((name) => filterIconLabel(name).toLowerCase().includes(term)),
	})).filter((group) => group.icons.length > 0)
})

const selected = computed(() => filterIconClass(icon.value))

function select(name: string, close: () => void) {
	icon.value = name
	close()
}

function clear(close: () => void) {
	icon.value = undefined
	close()
}
</script>

<template>
	<Popover>
		<template #trigger>
			<Button class="w-full !justify-start">
				<template #prefix>
					<span
						:class="selected || 'lucide-circle-dashed'"
						class="h-4 w-4 flex-shrink-0 text-ink-gray-7"
					/>
				</template>
				<span class="truncate">
					{{ selected ? filterIconLabel(selected) : __('Select an icon') }}
				</span>
			</Button>
		</template>
		<template #default="{ close }">
			<div class="flex w-64 flex-col p-2">
				<TextInput v-model="search" :placeholder="__('Search icons...')">
					<template #prefix>
						<span class="lucide-search h-4 w-4 text-ink-gray-5" />
					</template>
				</TextInput>
				<div class="mt-2 max-h-64 overflow-y-auto">
					<div v-for="group in groups" :key="group.label" class="mb-2 last:mb-0">
						<p class="px-1 pb-1 text-xs text-ink-gray-5">{{ __(group.label) }}</p>
						<div class="flex flex-wrap">
							<button
								v-for="name in group.icons"
								:key="name"
								type="button"
								:title="filterIconLabel(name)"
								class="flex h-8 w-8 items-center justify-center rounded-4 hover:bg-surface-gray-3"
								:class="{ 'bg-surface-gray-3': selected === name }"
								@click="select(name, close)"
							>
								<span :class="name" class="h-4 w-4 text-ink-gray-7" />
							</button>
						</div>
					</div>
					<p v-if="!groups.length" class="py-2 text-center text-base text-ink-gray-5">
						{{ __('No icons found') }}
					</p>
				</div>
				<button
					v-if="selected"
					type="button"
					class="mt-1 rounded-4 border-t px-2 py-1 text-left text-base text-ink-gray-6 hover:bg-surface-gray-3"
					@click="clear(close)"
				>
					{{ __('Remove icon') }}
				</button>
			</div>
		</template>
	</Popover>
</template>
