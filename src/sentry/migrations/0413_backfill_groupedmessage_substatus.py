# Generated by Django 2.2.28 on 2023-04-07 23:43

from django.db import migrations

from sentry.models import GroupStatus, GroupSubStatus
from sentry.new_migrations.migrations import CheckedMigration
from sentry.utils.query import RangeQuerySetWrapperWithProgressBar


def backfill_substatus(apps, schema_editor):
    Group = apps.get_model("sentry", "Group")

    for group in RangeQuerySetWrapperWithProgressBar(
        Group.objects.filter(status__in=(GroupStatus.UNRESOLVED, GroupStatus.IGNORED))
    ):
        if group.status == GroupStatus.UNRESOLVED and group.substatus is None:
            group.substatus = GroupSubStatus.ONGOING
        if group.status == GroupStatus.IGNORED and group.substatus is None:
            group.substatus = GroupSubStatus.UNTIL_ESCALATING


class Migration(CheckedMigration):
    # This flag is used to mark that a migration shouldn't be automatically run in production. For
    # the most part, this should only be used for operations where it's safe to run the migration
    # after your code has deployed. So this should not be used for most operations that alter the
    # schema of a table.
    # Here are some things that make sense to mark as dangerous:
    # - Large data migrations. Typically we want these to be run manually by ops so that they can
    #   be monitored and not block the deploy for a long period of time while they run.
    # - Adding indexes to large tables. Since this can take a long time, we'd generally prefer to
    #   have ops run this and not block the deploy. Note that while adding an index is a schema
    #   change, it's completely safe to run the operation after the code has deployed.
    is_dangerous = True

    dependencies = [
        ("sentry", "0412_org_integration_denormalization"),
    ]

    operations = [
        migrations.RunPython(
            backfill_substatus,
            reverse_code=migrations.RunPython.noop,
            hints={"tables": ["sentry_groupedmessage"]},
        ),
    ]