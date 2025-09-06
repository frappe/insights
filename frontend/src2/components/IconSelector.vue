<script setup lang="ts">
import { computed, ref, nextTick, watch } from 'vue'
import * as LucideIcons from 'lucide-vue-next'
import { Popover, Button } from 'frappe-ui'

const { FolderIcon, SearchIcon } = LucideIcons

const props = defineProps<{
	modelValue?: string
	availableIcons?: string[]
	columns?: number
	size?: 'sm' | 'md' | 'lg'
}>()

const emit = defineEmits<{
	'update:modelValue': [value: string | undefined]
}>()

const searchQuery = ref('')
const showPopover = ref(false)
const searchInput = ref<HTMLInputElement>()

const allIcons = [
	'ChevronUp',
	'ChevronDown',
	'ChevronLeft',
	'ChevronRight',
	'ArrowUp',
	'ArrowDown',
	'ArrowLeft',
	'ArrowRight',
	'ArrowUpRight',
	'ArrowUpLeft',
	'ArrowDownRight',
	'ArrowDownLeft',
	'Move',
	'RotateCw',
	'RotateCcw',
	'Maximize',
	'Minimize',
	'Maximize2',
	'Minimize2',
	'Expand',
	'Shrink',
	'ExternalLink',
	'Plus',
	'Minus',
	'X',
	'Check',
	'CheckCircle',
	'XCircle',
	'AlertCircle',
	'Info',
	'HelpCircle',
	'MoreHorizontal',
	'MoreVertical',
	'Menu',
	'MenuSquare',
	'Grid3X3',
	'Grid2X2',
	'List',
	'Layout',
	'BarChart3',
	'BarChart',
	'LineChart',
	'PieChart',
	'TrendingUp',
	'TrendingDown',
	'Activity',
	'Hash',
	'Calculator',
	'Target',
	'Zap',
	'Database',
	'Table',
	'Columns',
	'File',
	'FileText',
	'FileImage',
	'FileVideo',
	'FileAudio',
	'Folder',
	'FolderOpen',
	'Download',
	'Upload',
	'Save',
	'Edit',
	'Copy',
	'Clipboard',
	'Trash',
	'Archive',
	'Bookmark',
	'Tag',
	'Mail',
	'MessageSquare',
	'MessageCircle',
	'Phone',
	'Video',
	'Mic',
	'MicOff',
	'Volume2',
	'VolumeX',
	'Bell',
	'BellOff',
	'Share',
	'Send',
	'Reply',
	'Forward',
	'Calendar',
	'CalendarDays',
	'CalendarClock',
	'Clock',
	'Timer',
	'Stopwatch',
	'History',
	'User',
	'Users',
	'UserPlus',
	'UserMinus',
	'UserCheck',
	'UserX',
	'UserCircle',
	'Avatar',
	'Lock',
	'Unlock',
	'Shield',
	'ShieldCheck',
	'ShieldAlert',
	'Key',
	'Settings',
	'Cog',
	'Sliders',
	'Image',
	'Images',
	'Camera',
	'Music',
	'Play',
	'Pause',
	'Stop',
	'SkipForward',
	'SkipBack',
	'MapPin',
	'Map',
	'Navigation',
	'Compass',
	'Globe',
	'Home',
	'Building',
	'Store',
	'Sun',
	'Moon',
	'Cloud',
	'CloudRain',
	'CloudSnow',
	'Wind',
	'Thermometer',
	'Droplets',
	'Circle',
	'Square',
	'Triangle',
	'Diamond',
	'Heart',
	'Star',
	'Flag',
	'Wrench',
	'Tool',
	'Hammer',
	'Screwdriver',
	'Search',
	'Filter',
	'SortAsc',
	'SortDesc',
	'RefreshCw',
	'RefreshCcw',
	'Repeat',
	'Shuffle',
]

const icons = computed(() => {
	const baseIcons = props.availableIcons?.length ? props.availableIcons : allIcons

	if (!searchQuery.value) {
		return baseIcons
	}

	return baseIcons.filter((iconName) =>
		iconName.toLowerCase().includes(searchQuery.value.toLowerCase()),
	)
})

const columns = computed(() => props.columns || 8)

function getIconComponent(iconName: string) {
	const IconComponent = (LucideIcons as any)[iconName]
	return IconComponent || LucideIcons.ShieldQuestion
}

function selectIcon(iconName: string) {
	emit('update:modelValue', iconName === props.modelValue ? undefined : iconName)
	showPopover.value = false
	searchQuery.value = ''
}

watch(showPopover, (isOpen) => {
	if (isOpen) {
		nextTick(() => {
			searchInput.value?.focus()
		})
	} else {
		searchQuery.value = ''
	}
})

function handleKeydown(event: KeyboardEvent) {
	if (event.key === 'Escape') {
		showPopover.value = false
		searchQuery.value = ''
	}
}
</script>

<template>
	<Popover
		:show="showPopover"
		@update:show="showPopover = $event"
		placement="bottom-start"
		popoverClass="!min-w-fit"
	>
		<template #target="{ togglePopover }">
			<Button variant="outline" class="w-full justify-start text-left" @click="togglePopover">
				<template #prefix>
					<component
						v-if="modelValue"
						:is="getIconComponent(modelValue)"
						class="h-4 w-4"
						stroke-width="1.5"
					/>
					<FolderIcon v-else class="h-4 w-4" stroke-width="1.5" />
				</template>
				{{ modelValue || 'Choose an icon' }}
			</Button>
		</template>

		<template #body-main="{ togglePopover }">
			<div class="w-80 p-3" @keydown="handleKeydown">
				<div class="mb-3">
					<div class="relative">
						<SearchIcon
							class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400"
						/>
						<input
							ref="searchInput"
							v-model="searchQuery"
							type="text"
							placeholder="Search for icons..."
							class="w-full rounded-md border border-gray-200 bg-gray-50 py-2 pl-10 pr-3 text-sm focus:border-blue-500 focus:bg-white focus:outline-none"
						/>
					</div>
				</div>

				<div class="max-h-64 overflow-y-auto">
					<div
						class="grid gap-1"
						:style="{ gridTemplateColumns: `repeat(${columns}, 1fr)` }"
					>
						<div
							v-for="iconName in icons"
							:key="iconName"
							class="aspect-square cursor-pointer rounded-full p-1 hover:bg-gray-100 dark:hover:bg-zinc-800"
							:class="
								modelValue === iconName
									? 'bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-400'
									: ''
							"
							@click="selectIcon(iconName)"
							:title="iconName"
						>
							<component
								:is="getIconComponent(iconName)"
								class="h-4 w-4"
								stroke-width="1.5"
							/>
						</div>
					</div>
				</div>

				<div
					v-if="icons.length === 0"
					class="py-8 text-center text-sm text-gray-500 dark:text-zinc-300"
				>
					No icons found for "{{ searchQuery }}"
				</div>
			</div>
		</template>
	</Popover>
</template>
