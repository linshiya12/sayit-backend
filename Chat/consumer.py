from channels.generic.websocket import AsyncWebsocketConsumer
import json
from .models import *
from channels.db import database_sync_to_async
from .serializer import GroupMessageSerializer
from django.utils import timezone

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"chat_{self.room_name}"
        self.chatroom = await self.get_chatroom()
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
  

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json.get("message")
        if message:
            message_data = await self.create_message(message)
            await self.channel_layer.group_send(
                self.room_group_name, {
                    "type": "chat_message",
                    "messages": message_data
                }
            )

    @database_sync_to_async
    def get_chatroom(self):
        return ChatGroup.objects.get(group_name=self.room_name)
    
    @database_sync_to_async
    def create_message(self, new_message):
        msg_type = new_message.get("type", "text")
        body_text = new_message.get("text_message") 
        file_link = new_message.get("fileUrl")     

        chat_message = GroupMessage.objects.create(
            group=self.chatroom,
            author=self.user,
            body=body_text,
            file=file_link,
            file_type=msg_type
        )
        return GroupMessageSerializer(chat_message).data
    
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "messages": event["messages"],
        }))

class StatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_anonymous:
            await self.close()
            return

        await self.accept()
        await self.update_user_presence(True)
        self.rooms = await self.get_user_rooms()
        print("connected",self.user.id,self.user.is_online)

        for room in self.rooms:
            group_name = f"chat_{room.group_name}"
            await self.channel_layer.group_add(group_name, self.channel_name)
            
            await self.channel_layer.group_send(
                group_name, {
                    "type": "user_status_update",
                    "user_id": self.user.id,
                    "is_online": True
                }
            )

    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            now = timezone.now()
            await self.update_user_presence(False, now)
            print(self.user.id,self.user.is_online)
            for room in self.rooms:
                group_name = f"chat_{room.group_name}"
                await self.channel_layer.group_send(
                    group_name, {
                        "type": "user_status_update",
                        "user_id": self.user.id,
                        "is_online": False,
                        "last_seen": now.isoformat()
                    }
                )
                await self.channel_layer.group_discard(group_name, self.channel_name)

    @database_sync_to_async
    def get_user_rooms(self):
        return list(ChatGroup.objects.filter(members=self.user))

    @database_sync_to_async
    def update_user_presence(self, is_online, last_seen=None):
        update_fields = {'is_online': is_online}
        if last_seen:
            update_fields['last_seen'] = last_seen
        
        # This hits the DB
        self.user.__class__.objects.filter(id=self.user.id).update(**update_fields)
        
        # To confirm it saved, you would need to re-fetch or just print the value you sent:
        print(f"DATABASE UPDATE: User {self.user.id} set to {is_online}")

    async def user_status_update(self, event):
        # Sends status updates of OTHER users to this user's sidebar
        await self.send(text_data=json.dumps(event))