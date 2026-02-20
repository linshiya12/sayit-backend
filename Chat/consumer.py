from channels.generic.websocket import AsyncWebsocketConsumer
import json
from .models import *
from channels.db import database_sync_to_async
from .serializer import GroupMessageSerializer
from django.utils import timezone
from django_redis import get_redis_connection

MAX_VIDEOUSERS=2

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_anonymous:
            await self.close()
            return
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"chat_{self.room_name}"
        try:
            self.chatroom = await self.get_chatroom()
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()
        except ChatGroup.DoesNotExist:
            await self.close()
  

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
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
        return ChatGroup.objects.get(group_name=self.room_name,category='chat')
    
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
            "room_id": self.chatroom.id,
        }))
    async def user_status_update(self, event):
        await self.send(text_data=json.dumps(event))

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
        return list(ChatGroup.objects.filter(members=self.user,category='chat'))

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
    
    async def chat_message(self, event):
        pass


class VideoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user=self.scope["user"]
        if self.user.is_anonymous:
            await self.close(code=4001,reason="user is not authenticated")
            return
        self.video_room= self.scope['url_route']['kwargs']['room_name']
        self.video_group_name = f"video_{self.video_room}"
    
        self.videoroom=await self.get_video_room()
        if not self.video_room:
            await self.close(code=4004,reason="Room not found")
            return
        
        self.redis=get_redis_connection("default")
        self.cache_key=f"room:{self.video_group_name}:users"

        self.existing_users=await self.get_existing_users()
        if len(self.existing_users)>=MAX_VIDEOUSERS:
            await self.close(code=4002,reason="room is full")
            return 
        
        await self.channel_layer.group_add(self.video_group_name,self.channel_name)
        await self.accept()
        for user_id in self.existing_users:
            username=await self.get_username(user_id)
            await self.send(text_data=json.dumps({
                "type": "new_peer",
                "user": int(user_id),
                "peername" : username
            }))
        await database_sync_to_async (self.redis.sadd)(self.cache_key,self.user.id)
        await self.channel_layer.group_send(
            self.video_group_name,
            {
                'type':'broadcast.new_peer',
                'user':self.user.id,
                'peername':self.user.first_name
            }
        )
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type=data.get("type")
        print("dara",data)
        if message_type=="offer":
            await self.channel_layer.group_send(
                self.video_group_name,
            {
                "type": "broadcast.offer",
                "offer": data["offer"],
                "from_user": self.user.id,
                "to":data["to"]
            }
            )
        elif message_type=="answer":
            await self.channel_layer.group_send(
                self.video_group_name,
            {
                "type": "broadcast.answer",
                "answer": data["answer"],
                "from_user": self.user.id,
                "to":data["to"]
            }
            )
        if message_type=="ice":
            await self.channel_layer.group_send(
                self.video_group_name,
            {
                "type": "broadcast.ice",
                "candidate": data["candidate"],
                "from_user": self.user.id,
            }
            )
        
    async def disconnect(self, close_code):
        await database_sync_to_async (self.redis.srem)(self.cache_key,self.user.id)
        await self.channel_layer.group_send(
            self.video_group_name,
            {
                'type':'broadcast.user_left',
                'user':self.user.id,
            }
        )
        await self.channel_layer.group_discard(self.video_group_name,self.channel_name)


    @database_sync_to_async
    def get_video_room(self):
        return ChatGroup.objects.get(group_name=self.video_room,category="video")
    
    @database_sync_to_async
    def get_existing_users(self):
        users=self.redis.smembers(self.cache_key)
        print("users",users)
        return [user.decode("utf-8") for user in users]

    @database_sync_to_async
    def get_username(self,user_id):
        userdetails=User.objects.get(id=user_id)
        return userdetails.first_name
    
    async def broadcast_new_peer(self,event):
        if event["user"]!=self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'new_peer',
                'user': event['user'],
                'peername' : event["peername"]
            }))
    
    async def broadcast_user_left(self,event):
        await self.send(text_data=json.dumps({
            'type': 'user_left',
            'user': event['user']
        }))
    async def broadcast_offer(self,event):
        if event["from_user"]!=self.user.id:
            await self.send(text_data=json.dumps({
            'type': 'offer',
            "offer": event["offer"],
            "from": event["from_user"],
            "to": event["to"]
            }))
    
    async def broadcast_answer(self,event):
        if event["from_user"]!=self.user.id:
            await self.send(text_data=json.dumps({
            'type': 'answer',
            "answer": event["answer"],
            "from": event["from_user"],
            "to": event["to"]
            }))

    async def broadcast_ice(self,event):
        if event["from_user"]!=self.user.id:
            await self.send(text_data=json.dumps({
            'type': 'ice',
            "candidate": event["candidate"],
            "from": event["from_user"]
            }))