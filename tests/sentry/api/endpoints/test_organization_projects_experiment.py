from functools import cached_property

from django.urls import reverse

from sentry.models import OrganizationMember, OrganizationMemberTeam, Team
from sentry.models.project import Project
from sentry.testutils import APITestCase
from sentry.testutils.helpers.features import with_feature
from sentry.testutils.silo import region_silo_test

# @region_silo_test
# class TeamProjectsCreateTest(APITestCase):

#         resp = self.client.post(url, data={"name": "hello world", "slug": "foobar"})
#         assert resp.status_code == 409, resp.content

#     def test_with_default_rules(self):
#         user = self.create_user()
#         org = self.create_organization(owner=user)
#         team1 = self.create_team(organization=org, name="foo")

#         path = f"/api/0/teams/{org.slug}/{team1.slug}/projects/"

#         self.login_as(user=user)

#         response = self.client.post(path, data={"name": "Test Project"})

#         assert response.status_code == 201, response.content
#         project = Project.objects.get(id=response.data["id"])
#         assert project.name == "Test Project"
#         assert project.slug

#         assert Rule.objects.filter(project=project).exists()

#     def test_without_default_rules(self):
#         user = self.create_user()
#         org = self.create_organization(owner=user)
#         team1 = self.create_team(organization=org, name="foo")

#         path = f"/api/0/teams/{org.slug}/{team1.slug}/projects/"

#         self.login_as(user=user)

#         response = self.client.post(path, data={"name": "Test Project", "default_rules": False})

#         assert response.status_code == 201, response.content
#         project = Project.objects.get(id=response.data["id"])
#         assert project.name == "Test Project"
#         assert project.slug

#         assert not Rule.objects.filter(project=project).exists()

#     @with_feature("organizations:issue-alert-fallback-targeting")
#     def test_with_default_rule_fallback_targeting(self):
#         user = self.create_user()
#         org = self.create_organization(owner=user)
#         team1 = self.create_team(organization=org, name="foo")

#         path = f"/api/0/teams/{org.slug}/{team1.slug}/projects/"

#         self.login_as(user=user)

#         response = self.client.post(path, data={"name": "Test Project", "default_rules": True})

#         assert response.status_code == 201, response.content
#         project = Project.objects.get(id=response.data["id"])

#         rule = Rule.objects.filter(project=project).first()
#         assert (
#             rule.data["actions"][0]["fallthroughType"] == FallthroughChoiceType.ACTIVE_MEMBERS.value
#         )

#     def test_with_duplicate_explicit_slug(self):
#         user = self.create_user()
#         org = self.create_organization(owner=user)
#         team1 = self.create_team(organization=org, name="foo")
#         self.create_project(organization=org, teams=[team1], slug="test-project")

#         path = f"/api/0/teams/{org.slug}/{team1.slug}/projects/"

#         self.login_as(user=user)

#         response = self.client.post(path, data={"name": "Test Project", "slug": "test-project"})

#         assert response.status_code == 409, response.content


@region_silo_test
class OrganizationProjectsExperimentCreateTest(APITestCase):
    endpoint = "sentry-api-0-organization-projects-experiment"
    method = "post"
    p1 = "project-one"
    p2 = "project-two"

    def setUp(self):
        super().setUp()
        self.login_as(user=self.user)
        self.t1 = f"default-team-{self.user}"

    @cached_property
    def path(self):
        return reverse(self.endpoint, args=[self.organization.slug])

    def test_missing_permission(self):
        user = self.create_user()
        self.login_as(user=user)

        self.get_error_response(self.organization.slug, status_code=403)

    def test_missing_project_name(self):
        response = self.get_error_response(self.organization.slug, status_code=400)
        assert response.data == {"name": ["This field is required."]}

    def test_invalid_platform(self):
        response = self.get_error_response(
            self.organization.slug, name=self.p1, platform="invalid", status_code=400
        )
        assert response.data == {"platform": ["Invalid platform"]}

    @with_feature(["organizations:team-roles", "organizations:team-project-creation-all"])
    def test_valid_params(self):
        response = self.get_success_response(self.organization.slug, name=self.p1, status_code=201)
        team = Team.objects.get(slug=self.t1, name=self.t1, through_project_creation=True)
        assert not team.idp_provisioned
        assert team.organization == self.organization

        member = OrganizationMember.objects.get(user=self.user, organization=self.organization)

        assert OrganizationMemberTeam.objects.filter(
            organizationmember=member, team=team, is_active=True, role="admin"
        ).exists()

        project = Project.objects.get(id=response.data["id"])
        assert project.name == self.p1
        assert project.slug == self.p1
        assert project.teams.first() == team

    # def test_duplicate(self):
    #     self.get_success_response(
    #         self.organization.slug, name="hello world", slug="foobar", status_code=201
    #     )
    #     response = self.get_error_response(
    #         self.organization.slug, name="hello world", slug="foobar", status_code=409
    #     )
    #     assert response.data == {
    #         "non_field_errors": ["A team with this slug already exists."],
    #         "detail": "A team with this slug already exists.",
    #     }

    # def test_name_too_long(self):
    #     self.get_error_response(
    #         self.organization.slug, name="x" * 65, slug="xxxxxxx", status_code=400
    #     )

    # def test_org_member_does_not_exist_passes(self):
    #     prior_team_count = Team.objects.count()

    #     # Multiple calls are made to OrganizationMember.objects.get, so in order to only raise
    #     # OrganizationMember.DoesNotExist for the correct call, we set a reference to the actual
    #     # function then call the reference unless the organization matches the test case
    #     get_reference = OrganizationMember.objects.get

    #     def get_callthrough(*args, **kwargs):
    #         if self.organization in kwargs.values():
    #             raise OrganizationMember.DoesNotExist
    #         return get_reference(*args, **kwargs)

    #     with patch.object(OrganizationMember.objects, "get", side_effect=get_callthrough):
    #         resp = self.get_success_response(
    #             self.organization.slug, name="hello world", slug="foobar", status_code=201
    #         )
    #     team = Team.objects.get(id=resp.data["id"])
    #     assert team.name == "hello world"
    #     assert team.slug == "foobar"
    #     assert not team.idp_provisioned
    #     assert team.organization == self.organization

    #     member = OrganizationMember.objects.get(user=self.user, organization=self.organization)

    #     assert not OrganizationMemberTeam.objects.filter(
    #         organizationmember=member, team=team, is_active=True
    #     ).exists()
    #     assert Team.objects.count() == prior_team_count + 1

    # @with_feature(["organizations:team-roles", "organizations:team-project-creation-all"])
    # def test_valid_team_admin(self):
    #     prior_team_count = Team.objects.count()
    #     resp = self.get_success_response(
    #         self.organization.slug,
    #         name="hello world",
    #         slug="foobar",
    #         set_team_admin=True,
    #         status_code=201,
    #     )

    #     team = Team.objects.get(id=resp.data["id"])
    #     assert team.name == "hello world"
    #     assert team.slug == "foobar"
    #     assert not team.idp_provisioned
    #     assert team.organization == self.organization

    #     member = OrganizationMember.objects.get(user=self.user, organization=self.organization)

    #     assert OrganizationMemberTeam.objects.filter(
    #         organizationmember=member, team=team, is_active=True, role="admin"
    #     ).exists()
    #     assert Team.objects.count() == prior_team_count + 1

    # def test_team_admin_missing_team_roles_flag(self):
    #     response = self.get_error_response(
    #         self.organization.slug,
    #         name="hello world",
    #         slug="foobar",
    #         set_team_admin=True,
    #         status_code=404,
    #     )
    #     assert response.data == {
    #         "detail": "You do not have permission to join a new team as a team admin"
    #     }

    # @with_feature("organizations:team-roles")
    # def test_team_admin_missing_project_creation_all_flag(self):
    #     response = self.get_error_response(
    #         self.organization.slug,
    #         name="hello world",
    #         slug="foobar",
    #         set_team_admin=True,
    #         status_code=404,
    #     )
    #     assert response.data == {
    #         "detail": "You do not have permission to join a new team as a team admin"
    #     }

    # @with_feature(["organizations:team-roles", "organizations:team-project-creation-all"])
    # @patch.object(OrganizationTeamsEndpoint, "should_add_creator_to_team", return_value=False)
    # def test_team_admin_not_authenticated(self, mock_creator_check):
    #     response = self.get_error_response(
    #         self.organization.slug,
    #         name="hello world",
    #         slug="foobar",
    #         set_team_admin=True,
    #         status_code=400,
    #     )
    #     assert response.data == {
    #         "detail": "You do not have permission to join a new team as a Team Admin"
    #     }
    #     mock_creator_check.assert_called_once()

    # @with_feature(["organizations:team-roles", "organizations:team-project-creation-all"])
    # def test_team_admin_member_does_not_exist(self):
    #     prior_team_count = Team.objects.count()

    #     # Multiple calls are made to OrganizationMember.objects.get, so in order to only raise
    #     # OrganizationMember.DoesNotExist for the correct call, we set a reference to the actual
    #     # function then call the reference unless the organization matches the test case
    #     get_reference = OrganizationMember.objects.get

    #     def get_callthrough(*args, **kwargs):
    #         if self.organization in kwargs.values():
    #             raise OrganizationMember.DoesNotExist
    #         return get_reference(*args, **kwargs)

    #     with patch.object(OrganizationMember.objects, "get", side_effect=get_callthrough):
    #         response = self.get_error_response(
    #             self.organization.slug,
    #             name="hello world",
    #             slug="foobar",
    #             set_team_admin=True,
    #             status_code=403,
    #         )
    #         assert response.data == {
    #             "detail": "You must be a member of the organization to join a new team as a Team Admin",
    #         }
    #     assert Team.objects.count() == prior_team_count

    # @with_feature(["organizations:team-roles", "organizations:team-project-creation-all"])
    # @patch.object(OrganizationMemberTeam.objects, "create", side_effect=Exception("test"))
    # def test_team_admin_org_member_team_create_generically_fails(self, mock_create):
    #     prior_team_count = Team.objects.count()
    #     with pytest.raises(Exception):
    #         self.get_error_response(
    #             self.organization.slug,
    #             name="hello world",
    #             slug="foobar",
    #             set_team_admin=True,
    #             status_code=400,
    #         )
    #     mock_create.assert_called_once()
    #     assert Team.objects.count() == prior_team_count
    #     assert Team.objects.count() == prior_team_count
