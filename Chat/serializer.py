from user.serializer import UserSerializer
from rest_framework import serializers
from .models import *
from rest_framework.response import Response

class ChatGroupSerializer(serializers.ModelSerializer):
    members = UserSerializer(read_only=True, many=True)

    class Meta:
        model = ChatGroup
        fields = '__all__'

    def validate_group_name(self, value):
        if "_" in value:
            try:
                parts = value.split("_")
                id1 = int(parts[0])
                id2 = int(parts[1])
            
                if id1 > id2:
                    raise serializers.ValidationError("Room name IDs must be in ascending order (smaller_larger).")
            except Exception as e:
                raise serializers.ValidationError(f"Validation failed: {str(e)}")
        return value

class GroupMessageSerializer(serializers.ModelSerializer):
    group = ChatGroupSerializer(read_only=True)
    author = UserSerializer(read_only=True)

    class Meta:
        model = GroupMessage
        fields = '__all__'
    