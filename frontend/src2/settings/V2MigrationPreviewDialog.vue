<script setup lang="ts">
import { AlertTriangle, CheckCircle2, ExternalLink, XCircle } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { getErrorMessage } from '../helpers'
import { __ } from '../translation'
import useV2MigrationStore, {
	DashboardPreview,
	MigrationStatus,
	V2Dashboard,
	gapLabel,
	originLabel,
	summarizeCounts,
} from './v2_migration'

const props = defineProps<{
	dashboard: V2Dashboard | null
	status?: MigrationStatus
}>()
const emit = defineEmits<{
	(e: 'migrate', dashboard: V2Dashboard): void
	(e: 'open-workbook', target: { workbook: string | null; dashboard: string | null }): void
}>()

const show = defineModel({ required: true, default: false })

const store = useV2MigrationStore()
const preview = ref<DashboardPreview | null>(null)
const previewError = ref('')
const showReport = ref(false)

const state = computed(() => props.status?.status)
const migrated = computed(
	() => state.value === 'migrated' || Boolean(props.dashboard?.migrated_dashboard),
)
const failed = computed(() => state.value === 'failed')
const inFlight = computed(() => state.value === 'queued' || state.value === 'in_progress')

// A job's record expires, so `failed` does not last. The preview is re-run on
// every open, which makes it the durable account of why a dashboard will not
// migrate.
watch(
	() => [show.value, props.dashboard?.name],
	async () => {
		if (!show.value || !props.dashboard) return
		preview.value = null
		previewError.value = ''
		showReport.value = false
		try {
			preview.value = await store.previewDashboard(props.dashboard.name)
		} catch (err: any) {
			previewError.value = getErrorMessage(err)
		}
	},
	{ immediate: true },
)

// `dropped` separates a thing that vanished from a thing that converted with a
// visible downgrade. The two need different words, so they are shown apart.
const lostGaps = computed(() => preview.value?.gaps.filter((g) => g.dropped) || [])
const changedGaps = computed(() => preview.value?.gaps.filter((g) => !g.dropped) || [])
const countCards = computed(() => summarizeCounts(preview.value?.counts || {}))

const workbookTarget = computed(() => ({
	workbook: props.status?.workbook || props.dashboard?.migrated_workbook || null,
	dashboard: props.status?.dashboard || props.dashboard?.migrated_dashboard || null,
}))

const canMigrate = computed(
	() => Boolean(preview.value) && !previewError.value && !migrated.value && !inFlight.value,
)
</script>

<template>
	<Dialog
		v-model="show"
		:options="{ title: props.dashboard?.title || __('Preview Migration'), size: '2xl' }"
	>
		<template #body-content>
			<div class="flex max-h-[60vh] flex-col gap-4 overflow-y-auto text-base">
				<div v-if="store.previewing" class="flex items-center gap-2 py-8 text-ink-gray-6">
					<LoadingIndicator class="h-4 w-4" />
					<span>{{ __('Checking what will convert...') }}</span>
				</div>

				<div
					v-else-if="previewError"
					class="flex flex-col gap-1 rounded border border-outline-gray-2 bg-surface-gray-1 p-3"
				>
					<div class="flex items-center gap-2 font-medium text-ink-red-5">
						<XCircle class="h-4 w-4 shrink-0" />
						<span>{{ __('This dashboard could not be read') }}</span>
					</div>
					<p class="text-p-sm text-ink-gray-7">{{ previewError }}</p>
				</div>

				<template v-else-if="preview">
					<div
						v-if="failed"
						class="flex flex-col gap-1 rounded border border-outline-gray-2 bg-surface-gray-1 p-3"
					>
						<div class="flex items-center gap-2 font-medium text-ink-red-5">
							<XCircle class="h-4 w-4 shrink-0" />
							<span>{{ __('The last migration failed') }}</span>
						</div>
						<p class="text-p-sm text-ink-gray-7">
							{{ props.status?.error || __('No reason was reported.') }}
						</p>
						<p class="text-p-sm text-ink-gray-6">
							{{
								__(
									'The check below is re-run every time you open this, so it is the reliable account of what is wrong.',
								)
							}}
						</p>
					</div>

					<div
						v-else-if="migrated"
						class="flex items-start justify-between gap-3 rounded border border-outline-gray-2 bg-surface-gray-1 p-3"
					>
						<div class="flex flex-col gap-1">
							<div class="flex items-center gap-2 font-medium text-ink-green-3">
								<CheckCircle2 class="h-4 w-4 shrink-0" />
								<span>{{ __('Already migrated') }}</span>
							</div>
							<p class="text-p-sm text-ink-gray-6">
								{{
									__(
										'This dashboard has a v3 workbook. Migrating again will not change it.',
									)
								}}
							</p>
						</div>
						<Button
							v-if="workbookTarget.workbook"
							:label="__('Open Workbook')"
							variant="outline"
							@click="emit('open-workbook', workbookTarget)"
						>
							<template #suffix>
								<ExternalLink class="h-4 w-4" />
							</template>
						</Button>
					</div>

					<div
						v-else-if="inFlight"
						class="flex items-center gap-2 rounded border border-outline-gray-2 bg-surface-gray-1 p-3 font-medium text-ink-blue-3"
					>
						<LoadingIndicator class="h-4 w-4" />
						<span>{{ __('This dashboard is being migrated now.') }}</span>
					</div>

					<div
						v-else
						class="flex flex-col gap-1 rounded border border-outline-gray-2 bg-surface-gray-1 p-3"
					>
						<div
							v-if="preview.converts_cleanly"
							class="flex items-center gap-2 font-medium text-ink-green-3"
						>
							<CheckCircle2 class="h-4 w-4 shrink-0" />
							<span>{{ __('Converts cleanly') }}</span>
						</div>
						<div v-else class="flex items-center gap-2 font-medium text-ink-amber-3">
							<AlertTriangle class="h-4 w-4 shrink-0" />
							<span>{{ __('Converts with losses') }}</span>
						</div>
						<p class="text-p-sm text-ink-gray-6">
							{{
								preview.converts_cleanly
									? __('Every chart and query carries over to v3.')
									: __(
											'Some of this dashboard cannot be carried over. Read the list below before you migrate.',
									  )
							}}
						</p>
					</div>

					<div v-if="countCards.length" class="grid grid-cols-2 gap-2">
						<div
							v-for="card in countCards"
							:key="card.label"
							class="flex flex-col rounded border border-outline-gray-1 px-3 py-2"
						>
							<span class="text-lg font-medium text-ink-gray-8">{{
								card.value
							}}</span>
							<span class="text-p-sm text-ink-gray-6">{{ card.label }}</span>
							<span v-if="card.detail" class="text-p-sm text-ink-gray-5">
								{{ card.detail }}
							</span>
						</div>
					</div>

					<div
						v-if="preview.unresolved_data_sources.length"
						class="flex flex-col gap-1 rounded border border-outline-gray-1 p-3"
					>
						<div class="flex items-center gap-2">
							<AlertTriangle class="h-4 w-4 shrink-0 text-ink-amber-3" />
							<span class="font-medium text-ink-gray-8">
								{{ __('Data sources missing in v3') }}
							</span>
						</div>
						<p class="text-p-sm text-ink-gray-6">
							{{
								__(
									'Create these data sources in v3 first, or the migrated queries will have nothing to read.',
								)
							}}
						</p>
						<ul class="flex flex-wrap gap-1 pt-1">
							<li v-for="source in preview.unresolved_data_sources" :key="source">
								<Badge theme="amber" variant="subtle" :label="source" />
							</li>
						</ul>
					</div>

					<div v-if="lostGaps.length" class="flex flex-col gap-2">
						<h3 class="text-p-base font-medium text-ink-gray-8">
							{{ __('Will not carry over') }}
						</h3>
						<div
							v-for="(gap, idx) in lostGaps"
							:key="`lost-${idx}`"
							class="flex flex-col gap-1 rounded border border-outline-gray-1 p-3"
						>
							<div class="flex items-center gap-2">
								<XCircle class="h-4 w-4 shrink-0 text-ink-red-5" />
								<span class="font-medium text-ink-gray-8">
									{{ gapLabel(gap.kind) }}
								</span>
								<Badge
									theme="gray"
									variant="subtle"
									:label="originLabel(gap.origin)"
								/>
							</div>
							<p class="text-p-sm text-ink-gray-6">{{ gap.detail }}</p>
							<p v-if="gap.source" class="text-p-sm text-ink-gray-5">
								{{ __('In') }}: {{ gap.source }}
							</p>
						</div>
					</div>

					<div v-if="changedGaps.length" class="flex flex-col gap-2">
						<h3 class="text-p-base font-medium text-ink-gray-8">
							{{ __('Will look different in v3') }}
						</h3>
						<div
							v-for="(gap, idx) in changedGaps"
							:key="`changed-${idx}`"
							class="flex flex-col gap-1 rounded border border-outline-gray-1 p-3"
						>
							<div class="flex items-center gap-2">
								<AlertTriangle class="h-4 w-4 shrink-0 text-ink-amber-3" />
								<span class="font-medium text-ink-gray-8">
									{{ gapLabel(gap.kind) }}
								</span>
								<Badge
									theme="gray"
									variant="subtle"
									:label="originLabel(gap.origin)"
								/>
							</div>
							<p class="text-p-sm text-ink-gray-6">{{ gap.detail }}</p>
							<p v-if="gap.source" class="text-p-sm text-ink-gray-5">
								{{ __('In') }}: {{ gap.source }}
							</p>
						</div>
					</div>

					<div v-if="preview.report" class="flex flex-col gap-2">
						<Button
							class="self-start"
							variant="ghost"
							:label="showReport ? __('Hide Full Report') : __('Show Full Report')"
							@click="showReport = !showReport"
						/>
						<pre
							v-if="showReport"
							class="overflow-x-auto whitespace-pre-wrap rounded border border-outline-gray-1 bg-surface-gray-1 p-3 text-p-sm text-ink-gray-7"
							>{{ preview.report }}</pre
						>
					</div>
				</template>
			</div>
		</template>

		<template #actions>
			<div class="flex justify-end gap-2">
				<Button :label="__('Close')" variant="subtle" @click="show = false" />
				<Button
					v-if="canMigrate"
					:label="failed ? __('Retry Migration') : __('Migrate')"
					variant="solid"
					@click="props.dashboard && emit('migrate', props.dashboard)"
				/>
			</div>
		</template>
	</Dialog>
</template>
