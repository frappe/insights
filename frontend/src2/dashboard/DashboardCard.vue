<script setup lang="tsx">
import { BarChart2, Clock, Eye, MoreVertical, RefreshCw, Bookmark } from 'lucide-vue-next'
import { DashboardListItem } from './dashboards'

interface Props {
	dashboard: DashboardListItem
	dropdownOptions: any[]
	previewLoading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
	previewLoading: false,
})

const emit = defineEmits<{
	'toggle-favorite': []
	'update-preview': []
}>()
</script>

<template>
	<div class="group relative flex w-full cursor-pointer flex-col gap-2 rounded bg-white">
		<router-link
			:to="`/dashboards/${dashboard.name}`"
			class="flex h-[150px] overflow-hidden rounded shadow transition-transform duration-200 group-hover:scale-[1.01]"
		>
			<img
				v-if="dashboard.preview_image"
				:src="dashboard.preview_image"
				onerror="this.src = ''"
				class="object-cover opacity-80"
			/>
			<div
				v-else
				class="flex h-full w-full items-center justify-center bg-gray-50/70"
			>
				<Button
					variant="ghost"
					@click.prevent.stop="emit('update-preview')"
					:loading="previewLoading"
				>
					<template #prefix>
						<RefreshCw class="h-3.5 w-3.5 text-gray-500" />
					</template>
					<span class="text-gray-500">Load Preview</span>
				</Button>
			</div>
		</router-link>

		<div class="flex items-center justify-between gap-2">
			<div class="flex-1 min-w-0">
				<div class="flex items-start gap-1">
					<p class="truncate text-sm" :title="dashboard.title">
						{{ dashboard.title }}
					</p>
				</div>
				<div class="mt-1.5 flex gap-2">
					<div class="flex items-center gap-1">
						<Eye class="h-3 w-3 text-gray-600" stroke-width="1.5" />
						<span class="text-xs text-gray-600">
							{{ dashboard.views }}
						</span>
					</div>
					<div class="flex items-center gap-1">
						<BarChart2 class="h-3 w-3 text-gray-600" stroke-width="1.5" />
						<span class="text-xs text-gray-600">
							{{ dashboard.charts }}
						</span>
					</div>
					<div class="flex items-center gap-1">
						<Clock class="h-3 w-3 text-gray-600" stroke-width="1.5" />
						<span class="text-xs text-gray-600">
							{{ dashboard.modified_from_now }}
						</span>
					</div>
				</div>
			</div>
			<div class="flex flex-shrink-0 items-center">
				<button @click.stop="emit('toggle-favorite')">
					<Bookmark
						class="h-4 w-4"
						:class="{
							'fill-blue-500 text-blue-500 transition-all hover:scale-110 active:scale-90':
								dashboard.is_favourite,
							'text-[#9CA3AF] transition-all hover:scale-110 hover:text-[#374151] active:scale-90':
								!dashboard.is_favourite,
						}"
					/>
				</button>
				<Dropdown :options="dropdownOptions">
					<Button variant="ghost">
						<template #icon>
							<MoreVertical class="h-4 w-4 text-gray-700" stroke-width="1.5" />
						</template>
					</Button>
				</Dropdown>
			</div>
		</div>
	</div>
</template>
