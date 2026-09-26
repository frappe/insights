<script setup lang="tsx">
import { Avatar } from 'frappe-ui'
import { Eye, MoreVertical, RefreshCw, Star } from 'lucide-vue-next'
import { ref, watch } from 'vue'
import { __ } from '../translation'
import useUserStore from '../users/users'
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

const userStore = useUserStore()
const previewFailed = ref(false)
watch(
	() => props.dashboard.preview_image,
	() => (previewFailed.value = false),
)
</script>

<template>
	<div
		class="group/card relative flex w-full cursor-pointer flex-col gap-2 rounded-4 bg-surface-base"
	>
		<router-link
			:to="`/dashboards/${dashboard.name}`"
			class="flex h-[150px] overflow-hidden rounded-4 border border-outline-gray-2 transition-transform duration-200 group-hover/card:scale-[1.01]"
		>
			<img
				v-if="dashboard.preview_image && !previewFailed"
				:src="dashboard.preview_image"
				:alt="`Preview of ${dashboard.title}`"
				loading="lazy"
				decoding="async"
				@error="previewFailed = true"
				class="h-full w-full object-cover object-top opacity-80"
			/>
			<div v-else class="flex h-full w-full items-center justify-center bg-surface-gray-1/70">
				<Button
					v-if="dashboard.can_write"
					variant="ghost"
					@click.prevent.stop="emit('update-preview')"
					:loading="previewLoading"
				>
					<template #prefix>
						<RefreshCw class="h-3.5 w-3.5 text-ink-gray-4" />
					</template>
					<span class="text-ink-gray-4">{{ __('Load Preview') }}</span>
				</Button>
			</div>
		</router-link>
		<Button
			class="absolute right-2 top-2"
			:class="
				dashboard.is_favourite
					? ''
					: 'opacity-0 group-hover/card:opacity-100 focus-visible:opacity-100'
			"
			variant="subtle"
			:label="dashboard.is_favourite ? __('Remove from favorites') : __('Add to favorites')"
			@click.stop="emit('toggle-favorite')"
		>
			<template #icon>
				<Star
					class="h-4 w-4"
					:class="
						dashboard.is_favourite
							? 'fill-ink-amber-4 text-ink-amber-4'
							: 'text-ink-gray-3 hover:text-ink-gray-6'
					"
				/>
			</template>
		</Button>

		<div class="flex items-center justify-between gap-2">
			<div class="flex-1 min-w-0">
				<p class="truncate text-sm" :title="dashboard.title">
					{{ dashboard.title }}
				</p>
				<div class="mt-1.5 flex items-center gap-3">
					<div class="flex min-w-0 items-center gap-1.5">
						<Avatar
							class="shrink-0"
							size="xs"
							:label="userStore.getName(dashboard.owner) || dashboard.owner"
							:image="userStore.getImage(dashboard.owner)"
						/>
						<span class="truncate text-xs text-ink-gray-5">
							{{ userStore.getName(dashboard.owner) || dashboard.owner }}
						</span>
					</div>
					<div class="flex shrink-0 items-center gap-1">
						<Eye class="h-3 w-3 text-ink-gray-5" stroke-width="1.5" />
						<span class="text-xs text-ink-gray-5">{{ dashboard.views }}</span>
					</div>
					<span class="shrink-0 text-xs text-ink-gray-5">
						{{ dashboard.modified_from_now }}
					</span>
				</div>
			</div>
			<div class="flex flex-shrink-0 items-center">
				<Dropdown :options="dropdownOptions">
					<Button variant="ghost">
						<template #icon>
							<MoreVertical class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
						</template>
					</Button>
				</Dropdown>
			</div>
		</div>
	</div>
</template>
