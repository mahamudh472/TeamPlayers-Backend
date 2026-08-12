import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TeamPlayers.settings')
django.setup()

from apps.agency.models import Candidate, CandidateProfile, Job, Agency
from apps.agency.services.candidates import _process_multiple_candidates_in_background, get_job_candidates

def run_test():
    print("--- Refactoring Verification Test ---")
    
    # 1. Clean up existing test candidate profiles/candidates with test email
    test_email = "alpha@test.com"
    CandidateProfile.objects.filter(email=test_email).delete()
    
    agency = Agency.objects.first()
    job1 = Job.objects.filter(agency=agency)[0]
    job2 = Job.objects.filter(agency=agency)[1]
    
    print(f"Agency: {agency.name}")
    print(f"Job 1: {job1.title} (ID: {job1.id})")
    print(f"Job 2: {job2.title} (ID: {job2.id})")
    
    test_text_1 = f"""
Candidate: Alpha Candidate
Email: {test_email}
Phone: 111-222-3333
Location: San Francisco, CA
Skills: Python, Django
Experience: 3 years
"""
    
    print("\n[Step 1] Ingesting candidate for Job 1...")
    # This runs the task synchronously for testing since we run the internal function directly
    _process_multiple_candidates_in_background(test_text_1, agency.id, job1.id)
    
    # Check profile
    profile = CandidateProfile.objects.filter(agency=agency, email=test_email).first()
    assert profile is not None, "Profile not created!"
    print(f"  Profile Created: {profile.name} (Email: {profile.email})")
    
    # Check Candidate application under job1
    cand1 = Candidate.objects.filter(job=job1, profile=profile).first()
    assert cand1 is not None, "Candidate application under Job 1 not created!"
    print(f"  Candidate application under Job 1 found! ID: {cand1.id}, Status: {cand1.status}")
    
    test_text_2 = f"""
Candidate: Alpha Candidate (Updated Profile)
Email: {test_email}
Phone: 111-222-3333
Location: Seattle, WA
Skills: Python, Django, React
Experience: 4 years
"""
    
    print("\n[Step 2] Ingesting same candidate for Job 2...")
    _process_multiple_candidates_in_background(test_text_2, agency.id, job2.id)
    
    # Check profiles count
    profiles_count = CandidateProfile.objects.filter(agency=agency, email=test_email).count()
    assert profiles_count == 1, f"Expected 1 profile, found {profiles_count}! Profile was duplicated!"
    print(f"  Success: Profile was not duplicated. Profile count is 1.")
    
    # Verify profile fields were updated
    profile.refresh_from_db()
    assert profile.location == "Seattle, WA", f"Profile location not updated: {profile.location}"
    print(f"  Profile Location Updated to: {profile.location}")
    print(f"  Profile Skills Updated to: {profile.skills}")
    
    # Check Candidate application under job2
    cand2 = Candidate.objects.filter(job=job2, profile=profile).first()
    assert cand2 is not None, "Candidate application under Job 2 not created!"
    print(f"  Candidate application under Job 2 found! ID: {cand2.id}, Status: {cand2.status}")
    
    # Verify both candidates exist and are returned in job candidates list
    job1_candidates = list(get_job_candidates(agency, job1.id))
    job2_candidates = list(get_job_candidates(agency, job2.id))
    
    print("\n[Step 3] Checking candidates lists under each job...")
    print(f"  Job 1 candidates: {[c.name for c in job1_candidates]}")
    print(f"  Job 2 candidates: {[c.name for c in job2_candidates]}")
    
    assert cand1 in job1_candidates, "Candidate not showing in Job 1 candidates list!"
    assert cand2 in job2_candidates, "Candidate not showing in Job 2 candidates list!"
    print("\n  >>> VERIFICATION SUCCESSFUL! Candidates show up in both jobs under the new architecture! <<<")

if __name__ == "__main__":
    run_test()
