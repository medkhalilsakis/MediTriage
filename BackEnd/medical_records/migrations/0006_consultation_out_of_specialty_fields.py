from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('appointments', '0005_appointment_last_staff_action_at'),
        ('authentication', '0002_customuser_profile_image'),
        ('doctors', '0006_alter_doctorleave_status'),
        ('medical_records', '0005_doctoroperation'),
    ]

    operations = [
        migrations.AddField(
            model_name='consultation',
            name='out_of_specialty_confirmed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='consultation',
            name='out_of_specialty_opinion',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='consultation',
            name='out_of_specialty_validated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='consultation',
            name='out_of_specialty_validated_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='validated_out_of_specialty_consultations', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='consultation',
            name='redirect_note',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='consultation',
            name='redirect_to_colleague',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='consultation',
            name='redirected_appointment',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='out_of_specialty_origin_consultations', to='appointments.appointment'),
        ),
        migrations.AddField(
            model_name='consultation',
            name='redirected_to_doctor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='received_out_of_specialty_referrals', to='doctors.doctorprofile'),
        ),
    ]
