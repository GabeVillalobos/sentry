from django.db import IntegrityError, transaction
from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from sentry import audit_log, features
from sentry.api.base import region_silo_endpoint
from sentry.api.bases.organization import OrganizationEndpoint, OrganizationPermission
from sentry.api.endpoints.team_projects import ProjectSerializer
from sentry.api.exceptions import ConflictError, ResourceDoesNotExist
from sentry.api.serializers import serialize
from sentry.models import Project
from sentry.models.organization import Organization
from sentry.models.organizationmember import OrganizationMember
from sentry.models.organizationmemberteam import OrganizationMemberTeam
from sentry.models.team import Team
from sentry.signals import project_created, team_created
from sentry.utils.snowflake import MaxSnowflakeRetryError

CONFLICTING_TEAM_SLUG_ERROR = "A team with this slug already exists."

# This endpoint is intented to be available to all members of an
# organization so we include "project:read" in the POST scopes.


class OrgProjectPermission(OrganizationPermission):
    scope_map = {
        "POST": ["project:read", "project:write", "project:admin"],
    }


@region_silo_endpoint
class OrganizationProjectsExperimentEndpoint(OrganizationEndpoint):
    permission_classes = (OrgProjectPermission,)

    def post(self, request: Request, organization: Organization) -> Response:
        """
        Create a new Team and Project
        ``````````````````

        Create a new team where the user is set as Team Admin. The
        name of the team is automatically set as 'default-team-[username]'.
        If the name is taken, a suffix is added as needed (eg: ...-1, ...-2).
        Then create a new project bound to this team

        :pparam string organization_slug: the slug of the organization the
                                          team should be created for.
        :qparam string name: the name for the new project.
        :qparam string platform: the optional platform that this project is for.
        :qparam bool default_rules: create default rules (defaults to True)
        :auth: required
        """
        serializer = ProjectSerializer(data=request.data)

        if not serializer.is_valid():
            raise ValidationError(serializer.errors)

        if not request.user.is_authenticated:
            raise ValidationError(
                {"detail": "You do not have permission to join a new team as a Team Admin"},
            )

        result = serializer.validated_data

        if not features.has("organizations:team-roles", organization) or not features.has(
            "organizations:team-project-creation-all", organization
        ):
            raise ResourceDoesNotExist(
                detail="You do not have permission to join a new team as a team admin"
            )

        default_team_slug = f"default-team-{request.user.username}"
        slug_copy = default_team_slug

        # add suffix to default team name until name is available
        counter = 1
        while Team.objects.filter(organization=organization, slug=slug_copy).exists():
            slug_copy = f"{default_team_slug}-{counter}"
            counter += 1
        default_team_slug = slug_copy

        with transaction.atomic():
            try:
                with transaction.atomic():
                    team = Team.objects.create(
                        name=result.get("name") or result["slug"],
                        slug=result.get("slug"),
                        idp_provisioned=result.get("idp_provisioned", False),
                        organization=organization,
                        through_project_creation=True,
                    )
                    member = OrganizationMember.objects.get(
                        user=request.user, organization=organization
                    )
                    OrganizationMemberTeam.objects.create(
                        team=team,
                        organizationmember=member,
                        role="admin",
                    )
                    project = Project.objects.create(
                        name=result["name"],
                        slug=None,
                        organization=organization,
                        platform=result.get("platform"),
                    )
            except (IntegrityError, MaxSnowflakeRetryError):
                # We can only have a conflicting team slug and not a conflicting project slug
                # because when we create the project, the project slug will be set based on
                # the name. If the slug is taken then the model will automatically add a
                # suffix to the project slug to make it unique. This is different from the
                # added suffix to the team slug that we do above
                raise ConflictError(
                    {
                        "non_field_errors": [CONFLICTING_TEAM_SLUG_ERROR],
                        "detail": CONFLICTING_TEAM_SLUG_ERROR,
                    }
                )
            except OrganizationMember.DoesNotExist:
                raise PermissionDenied(
                    detail="You must be a member of the organization to join a new team as a Team Admin"
                )
            else:
                project.add_team(team)

            team_created.send_robust(
                organization=organization,
                user=request.user,
                team=team,
                sender=self.__class__,
            )
            self.create_audit_entry(
                request=request,
                organization=organization,
                target_object=team.id,
                event=audit_log.get_event_id("TEAM_ADD"),
                data=team.get_audit_log_data(),
            )
            self.create_audit_entry(
                request=request,
                organization=team.organization,
                target_object=project.id,
                event=audit_log.get_event_id("PROJECT_ADD"),
                data=project.get_audit_log_data(),
            )
            project_created.send(
                project=project,
                user=request.user,
                default_rules=result.get("default_rules", True),
                sender=self,
            )

        return Response(serialize(project, request.user), status=201)
