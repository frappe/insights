<script setup lang="ts">
import Toggle from '../../components/Toggle.vue'
import { __ } from '../../translation'

// Run as owner, and what it means for who sees which rows. The chart's share
// dialog sets it here, and the upgrade wizard pictures it.
const runAsOwner = defineModel<boolean>({ required: true })
const props = defineProps<{
	disabled?: boolean
	isPublic?: boolean
	/** Whether readers beyond those named one by one would see the owner's rows. */
	exposesOwnerRows?: boolean
	/** The published dashboard the chart is on, if any. */
	publishedByDashboard?: string | null
}>()
</script>

<template>
	<div class="flex flex-col gap-2">
		<div class="flex items-center justify-between gap-2">
			<span class="text-sm text-ink-gray-5">
				{{ __('Run as owner') }}
			</span>
			<Toggle v-model="runAsOwner" :disabled="props.disabled" />
		</div>
		<p v-if="props.isPublic || !props.exposesOwnerRows" class="text-sm text-ink-gray-5">
			{{
				runAsOwner
					? __(
							"Every reader sees the rows this chart's owner can see, and nothing behind the chart.",
					  )
					: props.isPublic
					  ? __(
								'Guests have no permissions of their own, so a public link shows them nothing until the chart runs as its owner.',
					    )
					  : __('Each reader sees the rows their own permissions allow.')
			}}
		</p>
		<p v-else class="text-sm text-ink-red-5">
			{{
				props.publishedByDashboard
					? __(
							"This chart is on the published dashboard {0}, so everyone who can open it will see the rows this chart's owner can see.",
							props.publishedByDashboard,
					  )
					: __(
							"Everyone will see the rows this chart's owner can see, including rows their own permissions would hide.",
					  )
			}}
		</p>
	</div>
</template>
