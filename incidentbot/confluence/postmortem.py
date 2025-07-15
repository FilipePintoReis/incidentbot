import datetime
import uuid

from incidentbot.configuration.settings import settings
from incidentbot.confluence.api import ConfluenceApi
from incidentbot.exceptions import PostmortemException
from incidentbot.models.database import (
    IncidentEvent,
    IncidentParticipant,
    IncidentRecord,
)
from incidentbot.logging import logger
from requests.exceptions import HTTPError
from incidentbot.slack.client import get_postmortem_channel_history
from incidentbot.slack.client import slack_web_client

from incidentbot.diagnostics.BedRockHandler import BedRockHandler
import json


class IncidentPostmortem:
    def __init__(
        self,
        incident: IncidentRecord,
        participants: list[IncidentParticipant],
        timeline: list[IncidentEvent],
        title: str,
    ):
        self.parent_page = settings.integrations.atlassian.confluence.parent
        self.space = settings.integrations.atlassian.confluence.space
        self.incident = incident
        self.participants = participants
        self.timeline = timeline
        self.title = title

        self.confluence = ConfluenceApi()
        self.exec = self.confluence.api

    def new_create(self) -> str | None:
        agent_input = self._generate_agent_input()
        agent_response = self._invoke_agent(agent_input)
        self._create_post_mortem(agent_response)
    
    def _generate_agent_input(self) -> dict:
        pass

    def _invoke_agent(self, agent_input: dict) -> str | None:
        pass

    def _create_post_mortem(self, agent_response: str) -> None:
        pass

    def create_agentic(self) -> str | None:
        """
        {
            "channel_id": "im-3000",
            "channel_name": "im-3000",
            "created_at": "2025-12-23 17:00",
            "resolved_at": "2025-12-23 19:00",
            "severity": "SEV1",
            "status": "RESOLVED",
            "title": "a postmortem",
            "slack_history": [
            {"user": "Mehdi", "timestamp": "2025-12-23 17:05", "message": "oh fire fire laptop is on fire"},
            {"user": "Luigi", "timestamp": "2025-12-23 17:10", "message": "Luigi grabbed firehose"},
            {"user": "Swati", "timestamp": "2025-12-23 17:15", "message": "Mehdi damped the cloth"},
            {"user": "Filipe", "timestamp": "2025-12-23 17:18", "message": "fire is out"},
            {"user": "Rohan", "timestamp": "2025-12-23 17:19", "message": "we are happy"},
            {"user": "Swarna", "timestamp": "2025-12-23 17:21", "message": "printer is damaged"}
            ],
            "owner": "Mehdi Kharatizadeh",
            "link": "https://jira.org/IM-3000"
            }
        """

        slack_history = get_postmortem_channel_history(self.incident.channel_id, self.incident.channel_name)
        owners = [p.user_name for p in self.participants if p.is_lead]
        if owners:
            owner = owners[0]
        else:
            owner = 'unknown'
        agent_input = {
            'channel_id': self.incident.channel_id,
            'channel_name': self.incident.channel_name,
            'created_at': self.incident.created_at.strftime("%Y-%m-%d %H:%M"),
            'resolved_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            'severity': self.incident.severity,
            'status': self.incident.status,
            'title': self.title,
            'slack_history': slack_history,
            'owner': owner,
            'link': self.incident.link,
        }

        agent_id = "XF3IEEO45Q"
        alias_id = "3LIJUD6ECM"

        agent_response: str = BedRockHandler.invoke_bedrock_agent(
            agent_id=agent_id,
            agent_alias_id=alias_id,
            input_text=json.dumps(agent_input, indent=2),
            enable_trace=True, 
            end_session=False
        )

        slack_web_client.chat_postMessage(
            channel=self.incident.channel_id,
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": agent_response
                    }
                },
            ]
        )
        
    def create(self) -> str | None:
        """
        Creates a postmortem page and returns the created page's URL
        """

        try:
            parent_page_id = self.exec.get_page_id(
                self.space, self.parent_page
            )
            logger.info(
                f"Creating postmortem {self.title} in Confluence space {self.space} under parent {self.parent_page}..."
            )

            # Fetch template content
            template = self.confluence.fetch_template(
                settings.integrations.atlassian.confluence.template_id
            )
            if template:
                # Get original template body
                html = template.body

                # !ib-inject-description
                html = html.replace(
                    "!ib-inject-description", self.incident.description
                )
                # !ib-inject-duration
                html = html.replace(
                    "!ib-inject-duration",
                    self.__get_duration(),
                )
                # !ib-inject-impact
                html = html.replace("!ib-inject-impact", self.incident.impact)
                # !ib-inject-components
                html = html.replace(
                    "!ib-inject-components", self.incident.components
                )
                # !ib-inject-severity
                html = html.replace(
                    "!ib-inject-severity", self.incident.severity
                )
                # !ib-inject-created-at
                html = html.replace(
                    "!ib-inject-created-at", str(self.incident.created_at)
                )
                # !ib-inject-updated-at
                html = html.replace(
                    "!ib-inject-updated-at", str(self.incident.updated_at)
                )
                # !ib-inject-participants
                html = html.replace(
                    "!ib-inject-participants", self.__generate_participants()
                )

                # Create postmortem doc
                if self.exec.page_exists(
                    space=self.space, title=self.parent_page
                ):
                    try:
                        self.exec.create_page(
                            self.space,
                            self.title,
                            html,
                            parent_id=parent_page_id,
                            type="page",
                            representation="storage",
                            editor="v2",
                        )
                        created_page_id = self.exec.get_page_id(
                            self.space, self.title
                        )
                        created_page_info = self.exec.get_page_by_id(
                            page_id=created_page_id
                        )
                        url = (
                            created_page_info["_links"]["base"]
                            + created_page_info["_links"]["webui"]
                        )
                    except HTTPError as error:
                        logger.error(
                            f"Error creating postmortem page: {error}"
                        )
                        raise PostmortemException(error)

                    try:
                        # Replace timeline tag if one exists
                        page = self.exec.get_page_by_id(
                            created_page_id, "body.storage"
                        )
                        html = page.get("body").get("storage").get("value")
                        html = html.replace(
                            "!ib-inject-timeline",
                            self.__generate_timeline(created_page_id),
                        )

                        self.exec.update_page(
                            created_page_id,
                            page.get("title"),
                            html,
                            parent_id=parent_page_id,
                            type="page",
                            representation="storage",
                        )

                        return url
                    except HTTPError as error:
                        logger.error(
                            f"Error updating postmortem page: {error}"
                        )
                        raise PostmortemException(error)
                else:
                    logger.error(
                        "Couldn't create postmortem page, does the parent page exist?"
                    )
                    raise PostmortemException(
                        "Couldn't create postmortem page, does the parent page exist?"
                    )
            else:
                return None
        except Exception as error:
            logger.error(f"Error generating postmortem: {error}")

    def __generate_participants(self) -> str:
        """
        Generates the postmortem section for participants detail
        """

        base = f'<table data-table-width="760" data-layout="default" ac:local-id="{str(uuid.uuid4())}"><tbody><tr><th><p><strong>Role</strong></p></th><th><p><strong>User</strong></p></th></tr>'
        all_items_formatted = ""
        for item in self.participants:
            all_items_formatted += f"<tr><td><p>{item.role.replace("_", " ").title()}</p></td><td><p>{item.user_name}</p></td></tr>"
        base += all_items_formatted
        base += "</tbody></table>"

        return base

    def __generate_timeline(self, created_page_id: str) -> str:
        """
        Generates the postmortem section for timeline detail
        """

        base = f'<table data-table-width="760" data-layout="default" ac:local-id="{str(uuid.uuid4())}"><tbody><tr><th><p><strong>Timestamp</strong></p></th><th><p><strong>Event</strong></p></th></tr>'
        all_items_formatted = ""
        for item in self.timeline:
            if item.image is not None:
                try:
                    # Attach content to document
                    self.exec.attach_content(
                        comment=item.title,
                        content=item.image,
                        content_type=item.mimetype,
                        name=item.title,
                        page_id=created_page_id,
                        space=settings.integrations.atlassian.confluence.space,
                        title=item.title,
                    )
                except Exception as error:
                    logger.error(
                        f"Error attaching file {item.title} to postmortem: {error}"
                    )

                all_items_formatted += f'<tr><td><p>{item.created_at}</p></td><td><p /><ac:image ac:align="center" ac:layout="center" ac:alt="{item.title}"><ri:attachment ri:filename="{item.title}" ri:version-at-save="1" /></ac:image><p /></td></tr>'
            else:
                all_items_formatted += f"<tr><td><p>{item.created_at}</p></td><td><p>{item.text}</p></td></tr>"
        all_items_formatted += (
            "<tr><td><p>&hellip;</p></td><td><p>&hellip;</p></td></tr>"
        )
        base += all_items_formatted
        base += "</tbody></table>"

        return base

    def __get_duration(self) -> str:
        duration = datetime.datetime.now() - self.incident.created_at
        seconds = duration.seconds
        hours = seconds // 3600
        minutes = (seconds // 60) % 60

        return f"{hours}h{minutes}m"
