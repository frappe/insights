import type { InjectionKey } from 'vue'
import type { Workbook } from './workbook'

// The key alone, so a component asking only "is there a workbook around me?"
// need not import the store — which reaches the router and the whole builder
// aggregate, neither of which an island mounts with.
export const workbookKey = Symbol() as InjectionKey<Workbook>
