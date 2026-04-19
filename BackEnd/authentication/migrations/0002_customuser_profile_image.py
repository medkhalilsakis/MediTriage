from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='profile_image',
            field=models.FileField(blank=True, null=True, upload_to='profile_images/%Y/%m/'),
        ),
    ]
