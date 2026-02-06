import json
import os
from difflib import SequenceMatcher

import frappe

from insights.decorators import insights_whitelist


def get_map_json_path(map_type: str) -> str:
    """Get file path for map JSON"""
    if map_type not in ("india", "world"):
        frappe.throw("Invalid map type")

    filename = "india.json" if map_type == "india" else "world_map.json"
    return os.path.join(frappe.get_app_path("insights"), "public", "maps", filename)


def extract_regions_from_geojson(map_type: str) -> list:
    """Extract region names from GeoJSON file"""
    file_path = get_map_json_path(map_type)

    if not os.path.exists(file_path):
        frappe.throw(f"Map file not found: {file_path}")

    with open(file_path, encoding="utf-8") as f:
        geojson = json.load(f)

    regions = set()
    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        name = props.get("name")
        if name:
            regions.add(str(name).strip())

    return regions


def normalize(name: str) -> str:
    """Normalize region name for comparison"""
    return str(name).lower().strip() if name else ""


def calculate_similarity(str1: str, str2: str) -> float:
    """Calculate similarity between two strings"""
    # Compare Normalized strings
    return SequenceMatcher(None, normalize(str1), normalize(str2)).ratio()


# Get chart config to update with region mappings
def get_chart_config(chart_name: str) -> dict:
    """Get chart config as dict"""
    if not frappe.db.exists("Insights Chart v3", chart_name):
        return {}

    chart = frappe.get_doc("Insights Chart v3", chart_name)
    config = chart.config or {}

    if isinstance(config, str):
        config = frappe.parse_json(config) or {}
    return config


def _get_region_mappings(chart_name: str, map_type: str) -> dict:
    """Get stored region mappings"""
    config = get_chart_config(chart_name)
    return config.get("region_mappings", {}).get(map_type, {})


def save_chart_config(chart_name: str, config: dict):
    """Save chart config"""
    chart = frappe.get_doc("Insights Chart v3", chart_name)
    chart.config = config
    chart.save(ignore_permissions=True)


@insights_whitelist()
def get_available_regions(map_type: str) -> dict:
    """Get all available regions for map type"""
    regions = extract_regions_from_geojson(map_type)
    return {"map_type": map_type, "regions": regions, "count": len(regions)}


@insights_whitelist()
def find_unresolved_regions(map_type: str, user_regions: list, chart_name: str) -> dict:
    """Find unresolved regions and suggest mappings"""
    available = extract_regions_from_geojson(map_type)
    normalized_map = {normalize(r): r for r in available}
    existing_mappings = _get_region_mappings(chart_name, map_type) if chart_name else {}

    resolved = []
    unresolved = []

    for region in user_regions:
        if not region:
            continue

		# Normalize regions
        region_str = str(region).strip()
        region_norm = normalize(region_str)

        # Check manual mapping
        if region_str in existing_mappings:
            resolved.append(
                {
                    "user_region": region_str,
                    "mapped_to": existing_mappings[region_str],
                    "method": "manual_mapping",
                }
            )
            continue

        # Check exact match
        if region_norm in normalized_map:
            resolved.append(
                {"user_region": region_str, "mapped_to": normalized_map[region_norm], "method": "exact_match"}
            )
            continue

        # Find fuzzy matches
        suggestions = [
            {"region": a, "similarity": round(calculate_similarity(region_str, a), 3)}
            for a in available
            if calculate_similarity(region_str, a) > 0.6
        ]
        suggestions.sort(key=lambda x: x["similarity"], reverse=True)

        unresolved.append({"user_region": region_str, "suggestions": suggestions[:5]})

    return {
        "map_type": map_type,
        "total_regions": len(user_regions),
        "resolved_count": len(resolved),
        "unresolved_count": len(unresolved),
        "resolved": resolved,
        "unresolved": unresolved,
    }


# Save mapped regions in chart config
@insights_whitelist()
def save_region_mappings(chart_name: str, map_type: str, mappings: dict) -> dict:
    """Save multiple region mappings for a chart"""
    if not frappe.db.exists("Insights Chart v3", chart_name):
        frappe.throw("Chart not found")

    available = extract_regions_from_geojson(map_type)
    for mapped_region in mappings.values():
        if mapped_region and mapped_region not in available:
            frappe.throw(f"Invalid mapped region: {mapped_region}")

    # Update config
    config = get_chart_config(chart_name)
    if "region_mappings" not in config:
        config["region_mappings"] = {}
    if map_type not in config["region_mappings"]:
        config["region_mappings"][map_type] = {}

    # Apply mappings
    for user_region, mapped_region in mappings.items():
        if mapped_region:
            config["region_mappings"][map_type][user_region] = mapped_region
        else:
            config["region_mappings"][map_type].pop(user_region, None)

    save_chart_config(chart_name, config)

    return {"success": True, "message": f"Saved {len(mappings)} region mappings"}
