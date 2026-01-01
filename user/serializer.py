from rest_framework import serializers
from .models import *
from .utils import validate_name,validate_password
from django.contrib.auth import authenticate

# from .models

class SpokenlangSerializer(serializers.ModelSerializer):
    class Meta:
        model=Spokenlang
        fields="__all__"

class UserSerializer(serializers.ModelSerializer):
    spoken_languages = SpokenlangSerializer(many=True)
    class Meta:
        model = User
        fields = "__all__"

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "password",
            "confirm_password",
        ]
    
    def validate(self, data):
        if User.objects.filter(email=data["email"]).exists():
            raise serializers.ValidationError("User with this email already exists.")

        if not validate_name(data["first_name"]):
            raise serializers.ValidationError("First name is invalid.")
        if not validate_name(data["last_name"]):
            raise serializers.ValidationError("Last name is invalid.")

        if not validate_password(data["password"]):
            raise serializers.ValidationError("Password is not strong enough.")

        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match.")

        return data

    
class OtpSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

        
class ResendOtpSerializer(serializers.Serializer):
    email = serializers.EmailField()

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    class Meta:
        model=User
        fields=["email","password"]
    def validate(self, data):
        email=data.get("email")
        password=data.get("password")
        if not User.objects.filter(email=email).exists():
            raise serializers.ValidationError("User with this email doesn't exists.")
        user=authenticate(username=email,password=password)
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")
        data["user"]=user
        return data
        
class ProfiledataSerializer(serializers.ModelSerializer):
    spoken_languages = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    hourlyrate = serializers.IntegerField(
        required=False,
        allow_null=True
    )
    class Meta:
        model=User
        fields=["email","role","hourlyrate","learning_language","spoken_languages","native_language"]

    def validate(self,data):
        print("dd",data)
        role=data.get("role")
        if role not in ["student", "mentor"]:
            raise serializers.ValidationError(
                "Role must be either student or mentor"
            )
        hourlyrate = data.get("hourlyrate")
        if hourlyrate not in ["",None] and hourlyrate <= 0:
            raise serializers.ValidationError("Hourly rate must be greater than zero")
        return data
    
    def update(self, instance, validated_data):
        instance.role = validated_data.get("role", instance.role)
        hourlyrate = validated_data.get("hourlyrate")
        if hourlyrate in ["",None]:
            print("hi")
            instance.hourlyrate=None
        else:
            instance.hourlyrate = int(hourlyrate)
        instance.learning_language = validated_data.get("learning_language", instance.learning_language)
        instance.native_language = validated_data.get("native_language", instance.native_language)
        spoken_langs = validated_data.get("spoken_languages", None)
        
        if spoken_langs is not None:
            if instance.native_language not in spoken_langs:
                spoken_langs.append(instance.native_language)
            spoken_lang_objs = []
            for lang_name in spoken_langs:
                obj, created = Spokenlang.objects.get_or_create(spoken_language=lang_name)
                spoken_lang_objs.append(obj)
            
            instance.spoken_languages.set(spoken_lang_objs)
        instance.is_onboarded=True
        instance.save()
        return instance


# forgetpasswordserializer        
class PasswordChangeSerializer(serializers.Serializer):
    reset_token = serializers.CharField()
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        if not validate_password(data["password"]):
            raise serializers.ValidationError("Password is not strong enough.")

        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match.")

        return data   
    
class PostSerializer(serializers.ModelSerializer):
    class Meta:
        model=Post
        fields=['media_url','media_type','description']
    def validate(self,data):
        if data["media_type"] not in ["video","image"]:
            raise serializers.ValidationError("Invalid media type")
        if data.get("description") and len(data["description"]) > 600:
            raise serializers.ValidationError("Description must be less than 600 characters")
        return data

class GetpostSerializer(serializers.ModelSerializer):
    user=UserSerializer(read_only=True)
    class Meta:
        model=Post
        fields="__all__"

class FollowSerializer(serializers.ModelSerializer):
    # following=UserSerializer(read_only=True)
    class Meta:
        model=Follow
        fields=["following"]
    def validate_following(self, value):
        request = self.context.get("request")
        
        if request.user == value:
            raise serializers.ValidationError("You cannot follow yourself")

        return value

        
        

# ********************************************************** adminSerializers**********************************************


class UserBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "is_blocked"]
        read_only_fields = ["id"]