import frappe


def execute():
    if not frappe.db.a_row_exists("Insights Query Transform"):
        return

    transforms = frappe.get_all(
        "Insights Query Transform",
        filters={"type": "Pivot", "options": ["is", "set"]},
        fields=["name", "options", "parent"],
    )

    for transform in transforms:
        options = frappe.parse_json(transform.options)
        new_options = {}

        # options.key = InsightsQueryColumn.column
        # since InsightsQueryColumn.label is the unique identifier so
        # that should be used instead of InsightsQueryColumn.column

        for key in ["column", "index", "value"]:
            # get the column name from the label
            column_label = frappe.db.get_value(
                "Insights Query Column",
                {"column": options.get(key), "parent": transform.parent},
                "label",
            )

            if column_label:
                new_options[key] = column_label

        frappe.db.set_value(
            "Insights Query Transform",
            transform.name,
            "options",
            frappe.as_json(new_options),
        )
