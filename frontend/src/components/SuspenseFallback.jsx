import { LoadingIndicator } from 'frappe-ui'
export default {
	name: 'SuspenseFallback',
	components: { LoadingIndicator },
	render() {
		return (
			<div class="flex h-full w-full flex-col items-center justify-center">
				<LoadingIndicator class="h-10 w-10 text-gray-400" />
			</div>
		)
	},
}
