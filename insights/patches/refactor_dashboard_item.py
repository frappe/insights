import random

import click
import frappe


def execute():
    if not frappe.db.exists("DocType", "Insights Query Chart"):
        return

    """
    Each Dashboard Item had a link to Chart record, which stores the query and chart config.
    This patch moves the query and chart config to the Dashboard Item record.
    It also replaces `markdown`, `filter_column`, `filter_links` and `filter_label`
    with single JSON field called `options`.
    """

    for item_name in frappe.get_all("Insights Dashboard Item", pluck="name"):
        try:
            item = frappe.get_doc("Insights Dashboard Item", item_name)
            if item.item_id and frappe.parse_json(item.options):
                continue

            item.item_id = random.randint(1, 999999)
            new_options = {}
            if item.item_type == "Text":
                new_options = {"markdown": item.markdown}

            if item.chart:
                chart = frappe.get_doc("Insights Query Chart", item.chart)
                old_config = frappe.parse_json(chart.config)
                old_options = old_config.get("options", {})
                if chart.type == "Number":
                    item.item_type = "Number"
                    new_options = {
                        "query": item.query,
                        "title": chart.title,
                        "column": old_config.get("valueColumn", {}).get("label"),
                        "suffix": old_options.get("suffix"),
                        "prefix": old_options.get("prefix"),
                        "decimals": old_options.get("decimals"),
                    }
                elif chart.type == "Progress":
                    item.item_type = "Progress"
                    targetType = old_config.get("targetType")
                    target = (
                        old_config.get("target", {}).get("label")
                        if targetType == "Column"
                        else old_config.get("target")
                    )
                    new_options = {
                        "query": item.query,
                        "title": chart.title,
                        "suffix": old_options.get("suffix"),
                        "prefix": old_options.get("prefix"),
                        "decimals": old_options.get("decimals"),
                        "target": target,
                        "targetType": targetType,
                        "progress": old_config.get("progressColumn", {}).get("label"),
                        "shorten": old_options.get("shorten"),
                    }
                elif chart.type == "Bar":
                    item.item_type = "Bar"
                    new_options = {
                        "query": item.query,
                        "title": chart.title,
                        "xAxis": old_config.get("labelColumn", {}).get("label"),
                        "yAxis": [v["label"] for v in old_config.get("valueColumn")],
                        "referenceLine": old_options.get("referenceLine", {}).get(
                            "label"
                        ),
                        "colors": old_options.get("colors"),
                        "rotateLabels": old_options.get("rotateLabels"),
                        "stack": old_options.get("stack"),
                        "invertAxis": old_options.get("invertAxis"),
                    }
                elif chart.type == "Line":
                    item.item_type = "Line"
                    new_options = {
                        "query": item.query,
                        "title": chart.title,
                        "xAxis": old_config.get("labelColumn", {}).get("label"),
                        "yAxis": [v["label"] for v in old_config.get("valueColumn")],
                        "referenceLine": old_options.get("referenceLine", {}).get(
                            "label"
                        ),
                        "colors": old_options.get("colors"),
                        "smoothLines": old_options.get("smoothLines"),
                        "showPoints": old_options.get("showPoints"),
                    }
                elif chart.type == "Pie":
                    item.item_type = "Pie"
                    new_options = {
                        "query": item.query,
                        "title": chart.title,
                        "xAxis": old_config.get("labelColumn", {}).get("label"),
                        "yAxis": old_config.get("valueColumn", {}).get("label"),
                        "maxSlices": old_options.get("maxSlices"),
                        "colors": old_options.get("colors"),
                        "labelPosition": old_options.get("labelPosition", {}).get(
                            "label"
                        ),
                        "inlineLabels": old_options.get("inlineLabels"),
                        "scrollLabels": old_options.get("scrollLabels"),
                    }
                elif chart.type == "Table":
                    item.item_type = "Table"
                    new_options = {
                        "query": item.query,
                        "title": chart.title,
                        "columns": [v["label"] for v in old_config.get("columns")],
                        "index": old_options.get("index"),
                        "showTotal": old_options.get("showTotal"),
                    }

            # remove falsy values from options
            new_options = {k: v for k, v in new_options.items() if v}
            item.options = new_options
            item.item_type = item.item_type or "Bar"
            item.db_update()

        except Exception as e:
            click.secho(f"Error at {item_name}: {e}", fg="red")
            frappe.log_error(title="Error in Insights Patch: Refactor Dashboard Item")
        finally:
            frappe.db.commit()

    item_id_by_chart_name = {
        item.chart: item.item_id
        for item in frappe.get_all(
            "Insights Dashboard Item",
            filters={"chart": ["is", "set"]},
            fields=["chart", "item_id"],
        )
    }

    for item_name in frappe.get_all(
        "Insights Dashboard Item", {"item_type": "Filter"}, pluck="name"
    ):
        try:
            item = frappe.get_doc("Insights Dashboard Item", item_name)
            if item.item_id and frappe.parse_json(item.options):
                continue

            filter_column = frappe.parse_json(item.filter_column)
            filter_links = frappe.parse_json(item.filter_links)
            new_filter_links = {}
            if filter_links:
                filtered_charts = filter_links.keys()
                for chart_name in filtered_charts:
                    if chart_name not in item_id_by_chart_name:
                        click.secho(f"Chart {chart_name} not found", fg="red")
                        continue
                    new_filter_links[item_id_by_chart_name[chart_name]] = filter_links[
                        chart_name
                    ]
            new_options = {
                "label": item.filter_label,
                "column": filter_column,
                "links": new_filter_links,
            }
            item.options = new_options
            item.db_update()
        except Exception as e:
            click.secho(f"Error at {item_name}: {e}", fg="red")
            frappe.log_error(title="Error in Insights Patch: Refactor Dashboard Item")
        finally:
            frappe.db.commit()
