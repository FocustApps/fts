from datetime import datetime
import os
from typing import Dict
from pydantic import BaseModel
import requests
from service_connections.chat_service import ChatService


class ReportModel(BaseModel):
    name: str
    errors: int
    failures: int
    skipped: int
    tests: int
    time: float
    timestamp: datetime
    hostname: str


class SlackService(ChatService):

    def send_message(self, webhook_url: str, message: str):
        """
        Sends a message to a Slack channel using a webhook URL
        """

        payload = {"text": message, "type": "mrkdwn"}
        payload.update({"username": "FTS"})
        payload.update({"icon_emoji": ":fenrir:"})
        response = requests.post(webhook_url, json=payload)

        if response.status_code != 200:
            raise ValueError(
                f"Request to Slack returned an error {response.status_code}, the response is:\n{response.text}"
            )

        return response

    def format_message(self, message: Dict) -> str:
        """
        Formats the message for Slack
        """
        report = ReportModel(**message)
        report.timestamp = datetime.strftime(report.timestamp, "%H:%M:%S %Y-%m-%d")
        report.name = os.getenv("REPORT_NAME", report.name)
        minutes, seconds = divmod(report.time, 60)
        parsed_message = (
            f":page_facing_up: *Report Name:* *{report.name}*\n"
            "----------------------------------------\n"
            f":bar_chart: *Tests:* `{report.tests}`\n"
            "----------------------------------------\n"
            f":x: *Failures:* `{report.failures}`\n"
            "----------------------------------------\n"
            f":warning: *Errors:* `{report.errors}`\n"
            "----------------------------------------\n"
            f":arrow_forward: *Skipped:* `{report.skipped}`\n"
            "----------------------------------------\n"
            f":stopwatch: *Runtime:* `{int(minutes)} minutes and {seconds:.2f} seconds`\n"
            "----------------------------------------\n"
            f":calendar: *Timestamp:* `{report.timestamp}`\n"
            "----------------------------------------\n"
            f":computer: *Hostname:* `{report.hostname}`"
        )
        if report.failures > 0:
            build_uri = (
                os.getenv("Build.BuildUri")
                or os.getenv("BUILD_URI")
            )
            parsed_message += (
                f"\n----------------------------------------\n"
                f":warning: <!here> *There are failures in the report* \n"
                f"<{build_uri}|View Build>"
            )
        return parsed_message
