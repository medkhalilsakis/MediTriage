from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('medical_records', '0003_medicalrecord_administrative_notes_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='medicalrecord',
            name='longitudinal_metrics',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='medicalrecord',
            name='specialty_assessments',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
