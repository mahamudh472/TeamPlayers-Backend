from django.db.models import QuerySet
from django.core.mail import send_mail
from django.conf import settings
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from apps.agency.models import Agency, AgencyMember, Activity
from apps.accounts.models import User
import secrets
import string


def get_agency_members(agency: Agency) -> QuerySet[AgencyMember]:
    """
    Returns active members of the agency (both accepted and pending).
    """
    return AgencyMember.objects.filter(agency=agency, is_active=True).select_related('user').order_by('created_at')

def update_agency_member_role(agency: Agency, current_user: User, member_id: int, new_role: str) -> AgencyMember:
    """
    Updates the role of a member in the agency. Only owners/admins can update roles,
    and admins cannot modify the owner's role or promote someone to owner.
    """
    current_member = AgencyMember.objects.filter(
        agency=agency, user=current_user, is_active=True, invitation_status='accepted'
    ).first()
    
    if not current_member or current_member.role not in ['owner', 'admin']:
        raise PermissionDenied("You do not have permission to update member roles.")

    target_member = AgencyMember.objects.filter(agency=agency, id=member_id).first()
    if not target_member:
        raise NotFound("Member not found.")

    # Permissions rules:
    # 1. Non-owner cannot change owner's role
    if target_member.role == 'owner' and current_member.role != 'owner':
        raise PermissionDenied("Only the owner can update the owner's role.")
        
    # 2. Non-owner cannot promote someone to owner
    if new_role == 'owner' and current_member.role != 'owner':
        raise PermissionDenied("Only the owner can transfer ownership / assign the owner role.")

    target_member.role = new_role
    target_member.save()

    Activity.objects.create(
        model='member',
        model_id=target_member.id,
        agency=agency,
        user=current_user,
        summary=f"Updated role of member {target_member.user.email} to {new_role}"
    )

    return target_member

def remove_agency_member(agency: Agency, current_user: User, member_id: int) -> None:
    """
    Removes a member from the agency. Only owners/admins can remove members.
    Admins cannot remove the owner or other admins.
    """
    current_member = AgencyMember.objects.filter(
        agency=agency, user=current_user, is_active=True, invitation_status='accepted'
    ).first()
    
    if not current_member or current_member.role not in ['owner', 'admin']:
        raise PermissionDenied("You do not have permission to remove members.")

    target_member = AgencyMember.objects.filter(agency=agency, id=member_id).first()
    if not target_member:
        raise NotFound("Member not found.")

    # Protection checks:
    # 1. Owner cannot be removed from here
    if target_member.role == 'owner':
        raise PermissionDenied("The owner cannot be removed.")
        
    # 2. Admin cannot remove another admin (only owner can remove admins)
    if target_member.role == 'admin' and current_member.role != 'owner':
        raise PermissionDenied("Only the owner can remove administrators.")

    Activity.objects.create(
        model='member',
        model_id=target_member.id,
        agency=agency,
        user=current_user,
        summary=f"Removed member {target_member.user.email} from agency"
    )

    # Delete membership record to allow re-invitation without unique constraint issues
    target_member.delete()

def invite_agency_member(agency: Agency, current_user: User, email: str, role: str, request) -> AgencyMember:
    """
    Invites a member to the agency.
    If user exists, creates a pending membership and emails them a secure confirmation link.
    If user doesn't exist, creates user with a random password, adds them directly, and emails credentials.
    """
    current_member = AgencyMember.objects.filter(
        agency=agency, user=current_user, is_active=True, invitation_status='accepted'
    ).first()
    
    if not current_member or current_member.role not in ['owner', 'admin']:
        raise PermissionDenied("You do not have permission to invite members.")

    email = email.strip().lower()
    user = User.objects.filter(email=email).first()

    if user:
        # Existing user path
        member = AgencyMember.objects.filter(agency=agency, user=user).first()
        if member:
            if member.invitation_status == 'accepted' and member.is_active:
                raise ValidationError("This user is already a member of this agency.")
            else:
                # Update existing pending/rejected/inactive membership
                member.role = role
                member.invitation_status = 'pending'
                member.is_active = True
                member.save()
        else:
            member = AgencyMember.objects.create(
                agency=agency,
                user=user,
                role=role,
                invitation_status='pending',
                is_active=True
            )

        # Generate a signed invite link (valid for 7 days)
        signer = TimestampSigner()
        token = signer.sign(str(member.id))
        accept_url = request.build_absolute_uri('/api/v1/agency/members/accept-invite/') + f'?token={token}'

        # Send invitation email
        subject = f"Invitation to join {agency.name} on TeamPlayers"
        body = (
            f"Hello,\n\n"
            f"You have been invited to join the agency '{agency.name}' as a {role.title()}.\n\n"
            f"Please click the link below to accept the invitation:\n"
            f"{accept_url}\n\n"
            f"If you did not expect this invitation, you can safely ignore this email.\n\n"
            f"Best regards,\n"
            f"TeamPlayers Team"
        )
        send_mail(
            subject,
            body,
            getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@teamplayers.com'),
            [email],
            fail_silently=False
        )
    else:
        # Non-existent user path
        # Generate random password
        alphabet = string.ascii_letters + string.digits + "!@#$%"
        password = "".join(secrets.choice(alphabet) for _ in range(12))
        user = User.objects.create_user(
            email=email,
            password=password,
            is_active=True
        )
        
        # Directly add to agency as accepted
        member = AgencyMember.objects.create(
            agency=agency,
            user=user,
            role=role,
            invitation_status='accepted',
            is_active=True
        )

        # Email credentials to user
        subject = f"Welcome to {agency.name} on TeamPlayers"
        login_url = f"{settings.FRONTEND_URL}/login"
        body = (
            f"Hello,\n\n"
            f"An account has been created for you on TeamPlayers, and you have been added to the agency '{agency.name}' as a {role.title()}.\n\n"
            f"Here are your login credentials:\n"
            f"Email: {email}\n"
            f"Password: {password}\n\n"
            f"You can log in to your account here:\n"
            f"{login_url}\n\n"
            f"Please make sure to change your password after logging in.\n\n"
            f"Best regards,\n"
            f"TeamPlayers Team"
        )
        send_mail(
            subject,
            body,
            getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@teamplayers.com'),
            [email],
            fail_silently=False
        )

    Activity.objects.create(
        model='member',
        model_id=member.id,
        agency=agency,
        user=current_user,
        summary=f"Invited {email} to agency as {role}"
    )

    return member

def accept_agency_invitation(token: str) -> AgencyMember:
    """
    Validates the invitation token and updates the status of the agency member to accepted.
    """
    signer = TimestampSigner()
    try:
        # Invitation link is valid for 7 days
        member_id_str = signer.unsign(token, max_age=60*60*24*7)
    except SignatureExpired:
        raise ValidationError("The invitation link has expired.")
    except BadSignature:
        raise ValidationError("Invalid invitation link.")

    try:
        member = AgencyMember.objects.get(id=int(member_id_str))
    except (AgencyMember.DoesNotExist, ValueError):
        raise ValidationError("Invitation not found.")

    if member.invitation_status == 'accepted':
        return member

    member.invitation_status = 'accepted'
    member.save()

    Activity.objects.create(
        model='member',
        model_id=member.id,
        agency=member.agency,
        user=member.user,
        summary=f"Accepted agency invitation"
    )

    return member
