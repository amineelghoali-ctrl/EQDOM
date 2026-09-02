# Generated manually for EQDOM Fast-Track.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="ClientProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cin_number", models.CharField(db_index=True, max_length=20, unique=True)),
                ("nom", models.CharField(max_length=100)),
                ("prenom", models.CharField(max_length=100)),
                ("telephone", models.CharField(max_length=30)),
                ("cnss_number", models.CharField(blank=True, max_length=30)),
                ("cmr_number", models.CharField(blank=True, max_length=30)),
                ("liveness_verified", models.BooleanField(default=False)),
                ("face_match_score", models.FloatField(default=0.0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"verbose_name": "profil client", "verbose_name_plural": "profils clients", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="CoreBankingDetails",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("produit", models.CharField(max_length=100)),
                ("mode_prelevement", models.CharField(max_length=100)),
                ("montant_credit", models.DecimalField(decimal_places=2, max_digits=12)),
                ("mensualite", models.DecimalField(decimal_places=2, max_digits=12)),
                ("nb_mensualites_total", models.PositiveIntegerField()),
                ("nb_mensualites_restantes", models.PositiveIntegerField()),
                ("nbr_impayes", models.PositiveIntegerField(default=0)),
                ("age_impayes_jours", models.PositiveIntegerField(default=0)),
                ("total_impaye", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("penalite_retard", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("int_retard_ttc", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("frais_justice", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("mt_restant_du", models.DecimalField(decimal_places=2, max_digits=12)),
                ("total_a_regler", models.DecimalField(decimal_places=2, max_digits=12)),
                ("date_dernier_reglement", models.DateField(blank=True, null=True)),
                ("client", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="core_banking_details", to="fasttrack.clientprofile")),
            ],
            options={"verbose_name": "détail Core Banking", "verbose_name_plural": "détails Core Banking"},
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("client_cin", models.CharField(db_index=True, max_length=20)),
                ("action", models.CharField(max_length=100)),
                ("status", models.CharField(choices=[("SUCCESS", "Succès"), ("FAILURE", "Échec"), ("PENDING", "En cours")], max_length=20)),
                ("response_time_ms", models.PositiveIntegerField(default=0)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("agent", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="fasttrack_audit_logs", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-timestamp"]},
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["client_cin", "timestamp"], name="fasttrack_a_client__ed98ef_idx"),
        ),
    ]
