<script setup>
const props = defineProps({
	templates: { type: Array, required: true },
	showStatus: { type: Boolean, default: true },
})
</script>

<template>
	<div class="grid grid-cols-3 gap-4 text-base">
		<div
			v-for="template in templates"
			:key="template.title"
			class="rounded border border-gray-300"
		>
			<div class="relative flex h-32 w-full items-center justify-center rounded-t bg-gray-50">
				<span class="text-sm text-gray-600"> Loading Preview... </span>
				<div v-if="showStatus" class="absolute top-2 right-2">
					<Badge
						variant="subtle"
						:theme="
							{
								'Pending Approval': 'orange',
								Approved: 'green',
								Rejected: 'red',
							}[template.status]
						"
					>
						{{ template.status }}
					</Badge>
				</div>
			</div>
			<div class="flex flex-col p-2">
				<div class="flex items-center justify-between">
					<div class="text-base font-bold">{{ template.title }}</div>
				</div>
				<div class="mt-1 text-sm text-gray-700">{{ template.description }}</div>
				<div class="mt-2 flex items-center gap-2">
					<Avatar :label="template.author_name" />
					<span class="text-sm text-gray-700">{{ template.author_name }}</span>
				</div>
			</div>
		</div>
	</div>
</template>
