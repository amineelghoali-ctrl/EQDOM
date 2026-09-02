from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("fasttrack", "0001_initial")]

    operations = [
        migrations.AddField(model_name="clientprofile", name="autres_telephones", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="clientprofile", name="date_naissance", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="clientprofile", name="drpp_number", field=models.CharField(blank=True, max_length=30)),
        migrations.AddField(model_name="clientprofile", name="employeur", field=models.CharField(blank=True, max_length=150)),
        migrations.AddField(model_name="clientprofile", name="total_engagement", field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.AddField(model_name="corebankingdetails", name="banque", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="corebankingdetails", name="code_dit", field=models.CharField(blank=True, max_length=30)),
        migrations.AddField(model_name="corebankingdetails", name="date_acceptation", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="corebankingdetails", name="date_derniere_echeance", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="corebankingdetails", name="date_financement", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="corebankingdetails", name="date_premiere_echeance", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="corebankingdetails", name="etat", field=models.CharField(default="ACTIF", max_length=50)),
        migrations.AddField(model_name="corebankingdetails", name="frais_report", field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.AddField(model_name="corebankingdetails", name="honoraires_avocat", field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.AddField(model_name="corebankingdetails", name="montant_compense", field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.AddField(model_name="corebankingdetails", name="montant_finance", field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.AddField(model_name="corebankingdetails", name="montant_precompte", field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.AddField(model_name="corebankingdetails", name="montant_solde_provision", field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.AddField(model_name="corebankingdetails", name="nbr_reports", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="corebankingdetails", name="numero_dossier", field=models.CharField(blank=True, max_length=30, null=True, unique=True)),
        migrations.AddField(model_name="corebankingdetails", name="provenance", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="corebankingdetails", name="revendeur", field=models.CharField(blank=True, max_length=150)),
        migrations.AddField(model_name="corebankingdetails", name="restructuration", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="corebankingdetails", name="situation", field=models.CharField(default="NORMAL", max_length=100)),
        migrations.AddField(model_name="corebankingdetails", name="date_situation", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="corebankingdetails", name="total_traite", field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
    ]
