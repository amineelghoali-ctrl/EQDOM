from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("fasttrack", "0002_add_as400_fields")]

    operations = [
        migrations.RenameIndex(
            model_name="auditlog",
            new_name="fasttrack_a_client__ae7cbd_idx",
            old_name="fasttrack_a_client__ed98ef_idx",
        ),
    ]
