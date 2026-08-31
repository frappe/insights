<script setup lang="ts">
import { Badge } from 'frappe-ui'
import { AlertTriangle, Check, X } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { __ } from '../translation'
import useV2MigrationStore, {
	DashboardScan,
	MigrationItem,
	Verification,
	VERDICT_LABELS,
	VERDICT_THEMES,
	itemTitle,
	noteSentence,
	verdictSentence,
	verificationSentence,
} from './v2_migration'

const props = defineProps<{ dashboard: DashboardScan | null }>()
const emit = defineEmits<{
	(e: 'migrate', dashboard: DashboardScan): void
	(e: 'open', dashboard: DashboardScan): void
}>()

const show = defineModel({ required: true, default: false })

const store = useV2MigrationStore()
const verification = ref<Verification | null>(null)

const status = computed(() =>
	props.dashboard ? store.statuses[props.dashboard.dashboard] : undefined,
)
const migrated = computed(() => props.dashboard?.verdict === 'migrated')
const inFlight = computed(
	() => status.value?.status === 'queued' || status.value?.status === 'in_progress',
)
const failed = computed(() => status.value?.status === 'failed')
const canMigrate = computed(() => Boolean(props.dashboard) && !migrated.value && !inFlight.value)

// The differing charts are named on the summary; the reason each one differs is
// one level down, which is what this reads.
watch(
	() => [show.value, props.dashboard?.dashboard],
	async () => {
		verification.value = null
		if (!show.value || !props.dashboard || !migrated.value) return
		verification.value = await store.getVerification(props.dashboard.dashboard)
	},
	{ immediate: true },
)

const itemsInOrder = computed(() => {
	const rank: Record<MigrationItem['state'], number> = { dropped: 0, changed: 1, ok: 2 }
	return [...(props.dashboard?.items || [])].sort((a, b) => rank[a.state] - rank[b.state])
})

/** Once a dashboard is migrated, what carried over is settled - how the numbers
 * compare is the live question, so it becomes the description. */
const description = computed(() => {
	if (!props.dashboard) return ''
	if (inFlight.value) return __('Migrating now.')
	if (failed.value) {
		return (
			status.value?.error ||
			__('The migration stopped before it wrote anything. Try it again.')
		)
	}
	if (migrated.value && props.dashboard.verification) {
		return (
			verificationSentence(props.dashboard.verification) || verdictSentence(props.dashboard)
		)
	}
	return verdictSentence(props.dashboard)
})

/** The job outranks the scan's verdict here for the reason the list uses: it ran
 * later, and it wrote. */
const badge = computed(() => {
	if (inFlight.value) return { label: __('Migrating'), theme: 'blue' as const }
	if (failed.value) return { label: __('Could not migrate'), theme: 'red' as const }
	const verdict = props.dashboard!.verdict
	return { label: VERDICT_LABELS[verdict], theme: VERDICT_THEMES[verdict] }
})

const differingQueries = computed(
	() => verification.value?.queries.filter((q) => q.verdict === 'different') || [],
)
</script>

<template>
	<Dialog
		v-if="props.dashboard"
		v-model="show"
		:options="{ title: props.dashboard.title, size: '2xl' }"
	>
		<template #body-title>
			<div class="flex items-center gap-2">
				<h3 class="text-2xl font-semibold leading-6 text-ink-gray-9">
					{{ props.dashboard.title }}
				</h3>
				<Badge variant="subtle" :theme="badge.theme" :label="badge.label" />
			</div>
		</template>

		<template #body-content>
			<div class="flex max-h-[60vh] flex-col gap-4 overflow-y-auto text-base">
				<p class="text-p-base text-ink-gray-7">
					{{ description }}
				</p>

				<ul v-if="differingQueries.length" class="flex flex-col gap-2">
					<li
						v-for="query in differingQueries"
						:key="query.query"
						class="flex flex-col gap-0.5"
					>
						<span class="text-p-sm font-medium text-ink-gray-8">
							{{ query.charts.join(', ') || query.query }}
						</span>
						<span
							v-for="(difference, idx) in query.differences"
							:key="idx"
							class="text-p-sm text-ink-gray-6"
						>
							{{ difference.detail }}
						</span>
					</li>
				</ul>

				<div class="flex flex-col gap-1">
					<h3 class="text-p-base font-medium text-ink-gray-8">
						{{ __('What is on this dashboard') }}
					</h3>
					<ul class="flex flex-col divide-y divide-outline-gray-1">
						<li
							v-for="item in itemsInOrder"
							:key="item.key"
							class="flex items-start gap-2 py-2"
						>
							<Check
								v-if="item.state === 'ok'"
								class="mt-0.5 h-4 w-4 shrink-0 text-ink-green-3"
							/>
							<AlertTriangle
								v-else-if="item.state === 'changed'"
								class="mt-0.5 h-4 w-4 shrink-0 text-ink-amber-3"
							/>
							<X v-else class="mt-0.5 h-4 w-4 shrink-0 text-ink-red-4" />
							<div class="flex min-w-0 flex-col gap-0.5">
								<span class="truncate text-p-base text-ink-gray-8">
									{{ itemTitle(item) }}
								</span>
								<span
									v-for="(note, idx) in item.notes"
									:key="idx"
									class="text-p-sm text-ink-gray-6"
								>
									{{ noteSentence(note) }}
								</span>
							</div>
						</li>
					</ul>
				</div>

				<div v-if="props.dashboard.queries.length" class="flex flex-col gap-1">
					<h3 class="text-p-base font-medium text-ink-gray-8">{{ __('Queries') }}</h3>
					<ul class="flex flex-col divide-y divide-outline-gray-1">
						<li
							v-for="section in props.dashboard.queries"
							:key="section.query"
							class="flex flex-col gap-0.5 py-2"
						>
							<span v-if="section.title" class="text-p-base text-ink-gray-8">
								{{ section.title }}
							</span>
							<span
								v-for="(note, idx) in section.notes"
								:key="idx"
								class="text-p-sm text-ink-gray-6"
							>
								{{ noteSentence(note) }}
							</span>
						</li>
					</ul>
				</div>
			</div>
		</template>

		<template #actions>
			<div class="flex justify-end gap-2">
				<Button :label="__('Close')" variant="subtle" @click="show = false" />
				<Button
					v-if="migrated"
					:label="__('Open in v3')"
					variant="solid"
					@click="emit('open', props.dashboard)"
				/>
				<Button
					v-else-if="canMigrate"
					:label="__('Migrate')"
					variant="solid"
					:loading="store.migrating"
					@click="emit('migrate', props.dashboard)"
				/>
			</div>
		</template>
	</Dialog>
</template>
