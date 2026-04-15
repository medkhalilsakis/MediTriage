# Generated manually on 2026-04-13

from django.db import migrations


def create_missing_doctor_profiles(apps, schema_editor):
    CustomUser = apps.get_model('authentication', 'CustomUser')
    DoctorProfile = apps.get_model('doctors', 'DoctorProfile')

    existing_user_ids = set(DoctorProfile.objects.values_list('user_id', flat=True))
    doctors_without_profile = CustomUser.objects.filter(role='doctor').exclude(id__in=existing_user_ids)

    for user in doctors_without_profile:
        base_license = f"AUTO-LIC-{user.id}"
        candidate = base_license
        suffix = 1

        while DoctorProfile.objects.filter(license_number=candidate).exists():
            candidate = f"{base_license}-{suffix}"
            suffix += 1

        DoctorProfile.objects.create(
            user_id=user.id,
            specialization='General specialist',
            department='general_medicine',
            license_number=candidate,
            years_of_experience=0,
            consultation_fee=0,
            bio='',
        )


def noop_reverse(apps, schema_editor):
    # Keep migrated data intact on reverse migration.
    return


class Migration(migrations.Migration):

    dependencies = [
        ('doctors', '0004_doctorleave_review_note_doctorleave_reviewed_at_and_more'),
    ]

    operations = [
        migrations.RunPython(create_missing_doctor_profiles, noop_reverse),
    ]
