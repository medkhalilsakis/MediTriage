from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Conversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_message_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='messaging_conversations_created', to=settings.AUTH_USER_MODEL)),
                ('participant_high', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messaging_conversations_high', to=settings.AUTH_USER_MODEL)),
                ('participant_low', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messaging_conversations_low', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-last_message_at', '-updated_at'],
            },
        ),
        migrations.CreateModel(
            name='DirectMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField()),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='messaging.conversation')),
                ('recipient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messaging_received_messages', to=settings.AUTH_USER_MODEL)),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messaging_sent_messages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='UserPresence',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_online', models.BooleanField(default=False)),
                ('last_seen', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='presence', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-last_seen'],
            },
        ),
        migrations.AddConstraint(
            model_name='conversation',
            constraint=models.UniqueConstraint(fields=('participant_low', 'participant_high'), name='messaging_unique_participant_pair'),
        ),
        migrations.AddConstraint(
            model_name='conversation',
            constraint=models.CheckConstraint(condition=~models.Q(participant_low=models.F('participant_high')), name='messaging_distinct_participants'),
        ),
        migrations.AddIndex(
            model_name='directmessage',
            index=models.Index(fields=['conversation', 'created_at'], name='messaging_di_convers_890020_idx'),
        ),
        migrations.AddIndex(
            model_name='directmessage',
            index=models.Index(fields=['recipient', 'is_read'], name='messaging_di_recipie_5c57e8_idx'),
        ),
    ]
