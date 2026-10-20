<script setup lang="tsx">
import { Avatar } from 'frappe-ui'
import { Eye, MoreVertical, Star } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { __ } from '../translation'
import useUserStore from '../users/users'
import DashboardLayoutSketch from './DashboardLayoutSketch.vue'
import { DashboardListItem } from './dashboards'

const props = defineProps<{
	dashboard: DashboardListItem
	dropdownOptions: any[]
}>()

const emit = defineEmits<{
	'toggle-favorite': []
}>()

// a reader without an Insights role cannot list users, and gets the owner's name
const userStore = props.dashboard.owner_name === undefined ? useUserStore() : null
const ownerName = computed(
	() =>
		props.dashboard.owner_name ||
		(props.dashboard.owner && userStore?.getName(props.dashboard.owner)) ||
		props.dashboard.owner ||
		'',
)
const previewFailed = ref(false)
watch(
	() => props.dashboard.preview_image,
	() => (previewFailed.value = false),
)
</script>

<template>
	<div class="group/card relative flex w-full flex-col gap-2 rounded-4 bg-surface-base">
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
			<DashboardLayoutSketch v-else :cells="dashboard.cells" />
		</router-link>
		<Button
			v-if="dropdownOptions.length"
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
			<router-link :to="`/dashboards/${dashboard.name}`" class="min-w-0 flex-1">
				<p class="truncate text-sm" :title="dashboard.title">
					{{ dashboard.title }}
				</p>
				<div class="mt-1.5 flex items-center gap-3">
					<div v-if="dashboard.shipped_by" class="flex min-w-0 items-center gap-1.5">
						<img
							v-if="dashboard.shipped_by_logo"
							:src="dashboard.shipped_by_logo"
							alt=""
							class="size-3.5 shrink-0 rounded-sm"
						/>
						<span class="truncate text-xs text-ink-gray-5">
							{{ dashboard.shipped_by }}
						</span>
					</div>
					<div v-else class="flex min-w-0 items-center gap-1.5">
						<Avatar
							class="shrink-0"
							size="xs"
							:label="ownerName"
							:image="dashboard.owner && userStore?.getImage(dashboard.owner)"
						/>
						<span class="truncate text-xs text-ink-gray-5">
							{{ ownerName }}
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
			</router-link>
			<div v-if="dropdownOptions.length" class="flex flex-shrink-0 items-center">
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
