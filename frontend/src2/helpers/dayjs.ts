import customParseFormat from 'dayjs/esm/plugin/customParseFormat'
import quarterOfYear from 'dayjs/esm/plugin/quarterOfYear'
import { dayjs } from 'frappe-ui'

dayjs.extend(quarterOfYear)
dayjs.extend(customParseFormat)

export default dayjs
