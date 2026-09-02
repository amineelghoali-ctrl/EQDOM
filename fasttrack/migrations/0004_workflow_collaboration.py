from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("fasttrack", "0003_rename_audit_log_index"),
    ]

    operations = [
        migrations.CreateModel(
            name="DossierWorkflow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("current_status", models.CharField(choices=[("SCAN_COMPLETED", "Scan terminé"), ("PENDING_DOCS", "Documents en attente"), ("PRE_APPROVED", "Pré-accord"), ("APPROVED", "Approuvé"), ("REJECTED", "Refusé")], default="SCAN_COMPLETED", max_length=20)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assigned_agent", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="assigned_workflows", to=settings.AUTH_USER_MODEL)),
                ("client", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="workflow", to="fasttrack.clientprofile")),
            ],
            options={"verbose_name": "workflow dossier", "verbose_name_plural": "workflows dossiers", "ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="WorkflowComment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("author", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="workflow_comments", to=settings.AUTH_USER_MODEL)),
                ("parent_comment", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="replies", to="fasttrack.workflowcomment")),
                ("workflow", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="comments", to="fasttrack.dossierworkflow")),
                ("likes", models.ManyToManyField(blank=True, related_name="liked_workflow_comments", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name": "commentaire workflow", "verbose_name_plural": "commentaires workflow", "ordering": ["created_at"]},
        ),
    ]
