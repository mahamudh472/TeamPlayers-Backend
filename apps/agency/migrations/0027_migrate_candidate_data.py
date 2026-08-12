from django.db import migrations

def migrate_candidates_to_profiles(apps, schema_editor):
    Candidate = apps.get_model('agency', 'Candidate')
    CandidateProfile = apps.get_model('agency', 'CandidateProfile')
    
    for cand in Candidate.objects.all():
        if not cand.profile_id:
            email = cand.email or f"no-email-{cand.id}@temp.com"
            profile, created = CandidateProfile.objects.get_or_create(
                agency=cand.agency,
                email=email,
                defaults={
                    'name': cand.name,
                    'phone': cand.phone,
                    'location': cand.location,
                    'experience': cand.experience,
                    'skills': cand.skills,
                    'current_salary': cand.current_salary,
                    'expected_salary': cand.expected_salary,
                    'resume': cand.resume,
                    'ai_extracted_raw_json': cand.ai_extracted_raw_json
                }
            )
            cand.profile = profile
            cand.save()

class Migration(migrations.Migration):

    dependencies = [
        ('agency', '0026_candidateprofile_candidate_profile'),
    ]

    operations = [
        migrations.RunPython(migrate_candidates_to_profiles, reverse_code=migrations.RunPython.noop),
    ]
