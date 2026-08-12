import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('agency', '0027_migrate_candidate_data'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='candidate',
            name='ai_extracted_raw_json',
        ),
        migrations.RemoveField(
            model_name='candidate',
            name='current_salary',
        ),
        migrations.RemoveField(
            model_name='candidate',
            name='email',
        ),
        migrations.RemoveField(
            model_name='candidate',
            name='expected_salary',
        ),
        migrations.RemoveField(
            model_name='candidate',
            name='experience',
        ),
        migrations.RemoveField(
            model_name='candidate',
            name='location',
        ),
        migrations.RemoveField(
            model_name='candidate',
            name='name',
        ),
        migrations.RemoveField(
            model_name='candidate',
            name='phone',
        ),
        migrations.RemoveField(
            model_name='candidate',
            name='resume',
        ),
        migrations.RemoveField(
            model_name='candidate',
            name='skills',
        ),
        migrations.AlterField(
            model_name='candidate',
            name='profile',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='candidates', to='agency.candidateprofile'),
        ),
    ]
