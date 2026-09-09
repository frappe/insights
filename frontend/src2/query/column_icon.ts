import { Calendar, Hash, Type } from 'lucide-vue-next'
import type { Component } from 'vue'
import { FIELDTYPES } from '../helpers/constants'

/** The icon that stands for a column's type, wherever a column is listed. */
export function columnIcon(type: string): Component {
	if (FIELDTYPES.NUMBER.includes(type)) return Hash
	if (FIELDTYPES.DATE.includes(type)) return Calendar
	return Type
}
