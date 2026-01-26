from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny,IsAuthenticated
from rest_framework import status
from .models import *
from .serializer import *
from django.shortcuts import get_object_or_404

# Create your views here.

class get_message(APIView):
    permission_classes=[IsAuthenticated]
    def get(self, request, room_name):
        group = get_object_or_404(ChatGroup, group_name=room_name,category='chat')
        
        if request.user not in group.members.all():
            return Response({"error": "Unauthorized"}, status=403)

        messages = group.chat_messages.all().order_by('created_at')

        serializer = GroupMessageSerializer(messages, many=True)
        return Response({"messages":serializer.data})
    

class get_create_chatroom(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        other_user_id = request.data.get("id")
        category = request.data.get("category")

        if not other_user_id or not category:
            return Response(
                {"error": "id and category are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if category not in ["chat", "video"]:
            return Response(
                {"error": "Invalid category"},
                status=status.HTTP_400_BAD_REQUEST
            )

        other_user = get_object_or_404(User, id=other_user_id)

        user_ids = sorted([user.id, other_user.id])

        if category=="chat":
            roomname = f"{user_ids[0]}_{user_ids[1]}"
        else:
            roomname = f"video_{user_ids[0]}_{user_ids[1]}"

        chatroom, created = ChatGroup.objects.get_or_create(
            group_name=roomname,
            is_private=True,
            category=category
        )

        if created:
            chatroom.members.add(user, other_user)

        serializer = ChatGroupSerializer(chatroom)

        return Response(
            {"chat_room": serializer.data},
            status=status.HTTP_200_OK
        )


class list_chatroom(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        chatroom=ChatGroup.objects.filter(is_private=True,members=request.user,category='chat')
        serializer=ChatGroupSerializer(chatroom,many=True)
        return Response(
            {"chat_room": serializer.data}, 
        )
        
       





