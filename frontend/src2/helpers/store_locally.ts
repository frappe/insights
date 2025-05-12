import { useStorage, watchDebounced } from '@vueuse/core'

type Props<T> = {
	key: keyof T
	namespace: string
	serializeFn: () => T
	defaultValue: T
}
export default function storeLocally<T>(props: Props<T>) {
	const serialized = props.serializeFn()
	const keyValue = serialized[props.key]
	const localData = useStorage<T>(`${props.namespace}:${keyValue}`, props.defaultValue)
	watchDebounced(props.serializeFn, (data) => (localData.value = data), {
		deep: true,
		debounce: 1000,
	})
	return localData
}
