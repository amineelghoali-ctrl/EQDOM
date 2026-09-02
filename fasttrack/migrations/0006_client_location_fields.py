from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("fasttrack", "0005_responsable_workflow_roles")]

    operations = [
        migrations.AddField(model_name="clientprofile", name="ville", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="clientprofile", name="adresse", field=models.CharField(blank=True, max_length=255)),
    ]
