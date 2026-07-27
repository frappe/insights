import { Avatar } from 'frappe-ui'
import { Building2, Eye, Lock, Shield } from 'lucide-vue-next'
import { __ } from '../translation'
import { WorkbookListItem } from '../types/workbook.types'
import useUserStore from '../users/users'

type Deps = {
	userStore: ReturnType<typeof useUserStore>
}

export function getWorkbookColumns(deps: Deps) {
	const { userStore } = deps

	return [
		{
			label: __('Title'),
			key: 'title',
			width: 4,
		},
		{
			label: __('Access'),
			key: 'shared_with',
			width: 2,
			getLabel: ({ row }: { row: WorkbookListItem }) => {
				if (row.shared_with_organization) return __('Everyone')
				if (!row.shared_with?.length) return __('Private')
				return row.shared_with.length > 1
					? `${row.shared_with.length} people`
					: userStore.getName(row.shared_with[0])
			},
			prefix: ({ row }: { row: WorkbookListItem }) => {
				if (row.shared_with_organization) return <Building2 class="h-3.5 w-3.5 text-blue-500" />
				if (!row.shared_with?.length) return <Lock class="h-3.5 w-3.5 text-orange-500" />
				return <Shield class="h-3.5 w-3.5 text-green-500" />
			},
		},
		{
			label: __('Views'),
			key: 'views',
			width: 1.5,
			getLabel: () => {},
			prefix: ({ row }: any) => (
				<div class="flex gap-1">
					<Eye class="h-3.5 w-3.5 text-gray-600" stroke-width="1.5" />
					<span class="font-mono text-sm text-gray-700">{row.views}</span>
				</div>
			),
		},
		{
			label: __('Owner'),
			key: 'owner',
			width: 2,
			getLabel: ({ row }: any) => userStore.getUser(row.owner)?.full_name || row.owner,
			prefix: ({ row }: any) => {
				const user = userStore.getUser(row.owner)
				return <Avatar size="md" label={row.owner} image={user?.user_image} />
			},
		},
		{
			label: __('Modified'),
			key: 'modified_from_now',
			width: 2,
			getLabel: ({ row }: any) => row.modified_from_now,
		},
	]
}
