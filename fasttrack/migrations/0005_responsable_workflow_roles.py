from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import migrations, models
import django.db.models.deletion


def create_profiles_and_backfill_workflows(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    UserProfile = apps.get_model("fasttrack", "UserProfile")
    DossierWorkflow = apps.get_model("fasttrack", "DossierWorkflow")

    for user in User.objects.all():
        UserProfile.objects.get_or_create(user_id=user.pk, defaults={"role": "AGENT"})

    responsable, created = User.objects.get_or_create(
        username="responsable_demo",
        defaults={
            "password": make_password("EqdomResponsable!2026"),
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
        },
    )
    UserProfile.objects.update_or_create(
        user_id=responsable.pk,
        defaults={"role": "RESPONSABLE"},
    )
    DossierWorkflow.objects.filter(created_by__isnull=True).update(
        created_by=models.F("assigned_agent")
    )
    DossierWorkflow.objects.filter(current_status="APPROVED").update(
        current_status="FINANCEMENT"
    )
    DossierWorkflow.objects.filter(current_status="REJECTED").update(
        current_status="REFUSE"
    )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("fasttrack", "0004_workflow_collaboration"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("role", models.CharField(choices=[("AGENT", "Agent"), ("RESPONSABLE", "Responsable")], default="AGENT", max_length=20)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="profile", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "profil utilisateur", "verbose_name_plural": "profils utilisateurs"},
        ),
        migrations.AddField(
            model_name="dossierworkflow",
            name="created_by",
            field=models.ForeignKey(blank=True, help_text="Agent ayant créé le dossier dans Fast-Track.", null=True, on_delete=django.db.models.deletion.PROTECT, related_name="created_workflows", to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name="dossierworkflow",
            name="current_status",
            field=models.CharField(choices=[("SCAN_COMPLETED", "Scan terminé"), ("PENDING_DOCS", "Documents en attente"), ("PRE_APPROVED", "Pré-accord"), ("PENDING_VALIDATION", "En attente de validation"), ("FINANCEMENT", "Financement"), ("REFUSE", "Refusé")], default="SCAN_COMPLETED", max_length=20),
        ),
        migrations.RunPython(create_profiles_and_backfill_workflows, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="dossierworkflow",
            name="created_by",
            field=models.ForeignKey(help_text="Agent ayant créé le dossier dans Fast-Track.", on_delete=django.db.models.deletion.PROTECT, related_name="created_workflows", to=settings.AUTH_USER_MODEL),
        ),
    ]
