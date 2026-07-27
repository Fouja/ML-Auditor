"""
WebSocket consumers for real-time features.
"""

import json

from channels.generic.websocket import AsyncWebsocketConsumer


class AlertsConsumer(AsyncWebsocketConsumer):
    """Consumer for real-time alerts."""

    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return

        self.room_group_name = f"alerts_{self.user.id}"

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name,
        )

    async def receive(self, text_data):
        """Receive message from WebSocket."""
        data = json.loads(text_data)
        message_type = data.get("type", "")

        if message_type == "subscribe":
            # Subscribe to specific alert types
            alert_type = data.get("alert_type", "all")
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "subscribed",
                        "alert_type": alert_type,
                    }
                )
            )

    async def alert_new(self, event):
        """Send new alert to WebSocket."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "new_alert",
                    "alert": event["alert"],
                }
            )
        )

    async def alert_update(self, event):
        """Send alert update to WebSocket."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "alert_update",
                    "alert": event["alert"],
                }
            )
        )


class AnalyticsConsumer(AsyncWebsocketConsumer):
    """Consumer for real-time analytics."""

    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return

        self.room_group_name = f"analytics_{self.user.id}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name,
        )

    async def analytics_update(self, event):
        """Send analytics update to WebSocket."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "analytics_update",
                    "data": event["data"],
                }
            )
        )


class NotificationsConsumer(AsyncWebsocketConsumer):
    """Consumer for real-time notifications."""

    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
            return

        self.room_group_name = f"notifications_{self.user.id}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name,
        )

    async def notification(self, event):
        """Send notification to WebSocket."""
        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification",
                    "notification": event["notification"],
                }
            )
        )
