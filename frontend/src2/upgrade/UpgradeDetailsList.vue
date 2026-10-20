<script setup lang="ts">
import { Check } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import session from '../session'
import { __ } from '../translation'
import upgrade from './upgrade'
import UpgradeSentence from './UpgradeSentence.vue'
import { sentenceOf, type ItemAction, type Row } from './upgrade_steps'

// What the upgrade changed that rarely needs anyone, in the wizard's sentences.
const router = useRouter()

function sentence(row: Row) {
	return sentenceOf(row.item, session.user.email, session.user.locale)
}

function openAction(action: ItemAction) {
	if (action.kind === 'fix') return
	const url = action.kind === 'form' ? action.url : router.resolve(action.route).href
	window.open(url, '_blank', 'noopener')
}

const isDone = (row: Row) => row.names.every((name) => upgrade.isDone(name))
</script>

<template>
	<div class="flex flex-col gap-4">
		<p v-if="!upgrade.details.length" class="py-6 text-center text-p-base text-ink-gray-5">
			{{ __('Nothing here.') }}
		</p>
		<div
			v-for="group in upgrade.details"
			:key="group.title"
			class="flex flex-col rounded-[10px] border border-outline-gray-2"
		>
			<div class="px-3 pb-1 pt-2 text-sm font-semibold text-ink-gray-8">
				{{ group.title }}
			</div>
			<div
				v-for="row in group.rows"
				:key="row.item.name"
				class="flex items-center gap-2.5 py-1.5 pl-3 pr-1.5 text-p-sm"
				:class="isDone(row) ? 'text-ink-gray-5 line-through' : 'text-ink-gray-7'"
			>
				<span class="flex-1">
					<UpgradeSentence :parts="sentence(row).text" />
					<template v-if="sentence(row).todo">
						{{ ' ' }}<UpgradeSentence :parts="sentence(row).todo!" />
					</template>
				</span>
				<Check
					v-if="isDone(row)"
					class="size-4 shrink-0 text-ink-green-7"
					stroke-width="1.5"
				/>
				<span v-else class="flex shrink-0 items-center gap-0.5">
					<Button
						v-if="row.item.action === 'delete_workbook' && row.item.can_fix"
						variant="ghost"
						size="sm"
						:label="__('Delete copy')"
						@click="upgrade.fix(row.item)"
					/>
					<Button
						v-if="sentence(row).action && sentence(row).action!.kind !== 'fix'"
						variant="ghost"
						size="sm"
						:label="sentence(row).action!.label"
						@click="openAction(sentence(row).action!)"
					/>
					<Button
						variant="ghost"
						size="sm"
						:tooltip="__('Done')"
						:aria-label="__('Done')"
						@click="upgrade.markDone(row.names)"
					>
						<template #icon
							><Check class="size-4 text-ink-gray-7" stroke-width="1.5"
						/></template>
					</Button>
				</span>
			</div>
		</div>
	</div>
</template>
