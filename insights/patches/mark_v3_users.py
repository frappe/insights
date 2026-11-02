from insights.upgrade import is_upgrade_migrate, mark_upgrade_unseen


def execute():
    if is_upgrade_migrate():
        mark_upgrade_unseen()
