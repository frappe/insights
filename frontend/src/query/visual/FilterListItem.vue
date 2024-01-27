<script setup>
import { fieldtypesToIcon } from '@/utils'
import { Sigma, X } from 'lucide-vue-next'

defineProps(['filter', 'isActive'])
defineEmits(['edit', 'remove'])

function isValidExpression(expression) {
	return expression?.raw && expression?.ast
}

function isValidFilter(filter) {
	if (isValidExpression(filter.expression)) return true
	const is_valid_column = filter.column.column || isValidExpression(filter.column.expression)
	return (
		is_valid_column &&
		filter.operator.value &&
		(filter.value.value || filter.operator.value.includes('is_'))
	)
}
</script>

<template>
	<div
		class="group relative flex h-8 w-full cursor-pointer items-center justify-between overflow-hidden rounded border border-gray-300 bg-white px-2 pl-2.5 hover:shadow"
		:class="isActive ? 'border-gray-500 bg-white shadow-sm ring-1 ring-gray-400' : ''"
		@click.prevent.stop="$emit('edit')"
	>
		<div class="absolute left-0 h-full w-1 flex-shrink-0 bg-green-600"></div>
		<div class="flex w-full items-center overflow-hidden">
			<div class="flex w-full space-x-2" v-if="isValidFilter(filter)">
				<template v-if="filter.expression?.raw">
					<component :is="Sigma" class="h-4 w-4 flex-shrink-0 text-gray-600" />
					<span class="truncate font-mono">{{ filter.expression.raw }}</span>
				</template>
				<template v-else>
					<div class="flex max-w-[60%] flex-shrink-0 gap-1 truncate">
						<component
							:is="fieldtypesToIcon[filter.column.type]"
							class="h-4 w-4 flex-shrink-0 text-gray-600"
						/>
						{{ filter.column.label || filter.column.column }}
					</div>
					<span class="flex-shrink-0 font-medium text-green-600">
						{{ filter.operator.value }}
					</span>
					<span
						v-if="!filter.operator.value.includes('is_')"
						class="flex-1 flex-shrink-0 truncate"
					>
						{{ filter.value.label || filter.value.value }}
					</span>
				</template>
			</div>
			<div v-else class="text-gray-600">Select a filter</div>
		</div>
		<div class="flex items-center">
			<X
				class="invisible h-4 w-4 text-gray-600 transition-all hover:text-gray-800 group-hover:visible"
				@click.prevent.stop="$emit('remove')"
			/>
		</div>
	</div>
</template>
