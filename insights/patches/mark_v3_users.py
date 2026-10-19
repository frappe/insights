from insights.upgrade import mark_v3_users, was_on_v3


def execute():
    if was_on_v3():
        mark_v3_users()
