from django.db import models
import shortuuid
from .enums import FileType,CategoryType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from user.models import User
import shortuuid
from django.contrib.auth import get_user_model

# Create your models here.

# chat_room
# chat_message
# room_members
# seen_by

User = get_user_model()

class ChatGroup(models.Model):
    group_name=models.CharField(max_length=128, unique=True, default=shortuuid.uuid)
    members=models.ManyToManyField(User, related_name='chat_members',blank=True)
    is_private = models.BooleanField(default=False)
    category=models.CharField(
        choices=FileType.choices, 
        max_length=15, 
        default=CategoryType.CHAT
    )
    def __str__(self):
        return self.group_name

class GroupMessage(models.Model):
    group=models.ForeignKey(ChatGroup, related_name='chat_messages', on_delete=models.CASCADE)
    author=models.ForeignKey(User,related_name='chat_sender', on_delete=models.CASCADE)
    body=models.CharField(max_length=1000,blank=True, null=True)
    file = models.URLField(max_length=500, blank=True, null=True)
    file_type = models.CharField(
        choices=FileType.choices, 
        max_length=15, 
        default=FileType.TEXT
    )
    created_at=models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.group.group_name
    
    
    




# class ChatRoom(models.Model):
#     id = models.UUIDField(
#         primary_key=True,
#         default=uuid.uuid4,
#         editable=False
#     )
#     room_name=models.CharField(max_length=20, blank=True, null=True)
#     room_type = models.CharField(choices=RoomType , max_length=12 )


# class TextMessage(models.Model) :
#     message = models.CharField(max_length=50)


# class FileMessage(models.Model):
#     message = models.FileField( upload_to="mesages/files")  
#     file_type = models.CharField(choices = FileType.choices , max_length=15) 

# class VideoCallHistory(models.Model):
#     start_time =models.DateTimeField(auto_now=True) 
#     end_time =models.DateTimeField(auto_now_add=True) 

# class ChatMessage(models.Model):
#     sender  = models.ForeignKey(User, related_name='sender', on_delete=models.DO_NOTHING)
#     content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    
#     # ID of the object in that model
#     object_id = models.PositiveIntegerField()
    
#     # Actual object (virtual field)
#     message = GenericForeignKey('content_type', 'object_id')

#     created_at=models.DateTimeField(auto_now=True)
#     updated_at=models.DateTimeField(auto_now_add=True)

# class SeenBy(models.Model):
#     message=models.ForeignKey('ChatMessage', related_name='seenmessage', on_delete=models.CASCADE)
#     seen_by= models.ForeignKey(User, related_name='seenby', on_delete=models.CASCADE)
#     created_at=models.DateTimeField(auto_now_add=False)



    




