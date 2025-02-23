from __future__ import annotations

from typing import Sequence

from rest_framework import serializers

from sentry.models import ActorTuple, Team, User
from sentry.services.hybrid_cloud.user import RpcUser
from sentry.services.hybrid_cloud.user.service import user_service


def extract_user_ids_from_mentions(organization_id, mentions):
    """
    Extracts user ids from a set of mentions. Mentions should be a list of
    `ActorTuple` instances. Returns a dictionary with 'users' and 'team_users' keys.
    'users' is the user ids for all explicitly mentioned users, and 'team_users'
    is all user ids from explicitly mentioned teams, excluding any already
    mentioned users.
    """
    actors: Sequence[RpcUser | Team] = ActorTuple.resolve_many(mentions)
    actor_mentions = separate_resolved_actors(actors)

    team_users = user_service.get_many(
        filter={
            "organization_id": organization_id,
            "team_ids": [t.id for t in actor_mentions["teams"]],
        }
    )
    mentioned_team_users = {u.id for u in team_users} - set({u.id for u in actor_mentions["users"]})

    return {
        "users": {user.id for user in actor_mentions["users"]},
        "team_users": set(mentioned_team_users),
    }


def separate_actors(actors):
    users = [actor for actor in actors if actor.type is User]
    teams = [actor for actor in actors if actor.type is Team]

    return {"users": users, "teams": teams}


def separate_resolved_actors(actors: Sequence[RpcUser | Team]):
    users = [actor for actor in actors if actor.class_name() == "User"]
    teams = [actor for actor in actors if isinstance(actor, Team)]

    return {"users": users, "teams": teams}


class MentionsMixin:
    def validate_mentions(self, mentions):
        if mentions and "projects" in self.context:

            separated_actors = separate_actors(mentions)
            # Validate that all mentioned users exist and are on the project.
            users = separated_actors["users"]

            mentioned_user_ids = {user.id for user in users}

            projects = self.context["projects"]
            organization_id = self.context["organization_id"]
            users = user_service.get_many(
                filter={
                    "user_ids": mentioned_user_ids,
                    "organization_id": organization_id,
                    "project_ids": [p.id for p in projects],
                },
            )
            user_ids = [u.id for u in users]

            if len(mentioned_user_ids) > len(user_ids):
                raise serializers.ValidationError("Cannot mention a non team member")

            # Validate that all mentioned teams exist and are on the project.
            teams = separated_actors["teams"]
            mentioned_team_ids = {team.id for team in teams}
            if (
                len(mentioned_team_ids)
                > Team.objects.filter(
                    id__in=mentioned_team_ids, projectteam__project__in=projects
                ).count()
            ):
                raise serializers.ValidationError(
                    "Mentioned team not found or not associated with project"
                )

        return mentions
