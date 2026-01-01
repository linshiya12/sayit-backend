from rest_framework.views import APIView
from rest_framework.response import Response
from .serializer import *
from rest_framework import status
from .utils import send_code_to_user,verify_otp,Pass_verify_otp
from .models import User,Spokenlang
from rest_framework.permissions import AllowAny,IsAuthenticated
from django.core.cache import cache
from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth import authenticate
from django.conf import settings
import uuid
import boto3

class HomeView(APIView):
    def get(self, request):
        return Response({"message": "hello"})
    
class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.COOKIES.get("refresh_token")
            print("refr",refresh_token)
            if not refresh_token:
                return Response(
                    {"message": "Refresh token not found"},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            request.data["refresh"] = refresh_token
            response = super().post(request, *args, **kwargs)

            refresh = RefreshToken(refresh_token)
            user = User.objects.get(id=refresh["user_id"])

            response.data["user"] = {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "is_onboarded":user.is_onboarded,
                "is_superuser":user.is_superuser,
                "role":user.role
            }

            return response

        except Exception as e:
            return Response(
                {"message": "Something went wrong", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class RegisterApi(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        data=request.data
        print("data",data)
        serializer=SignupSerializer(data=data)
        if serializer.is_valid():
            data=serializer.validated_data
            temp_id=data["email"]
            cache.set(f"data_{temp_id}", data, timeout=300)
            send_code_to_user(temp_id)
            return Response(
                {
                    "massage":"otp sent successfully"
                    },
                status=status.HTTP_201_CREATED
            )
        print(serializer.errors)
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
    
class VerifyOtpApi(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = OtpSerializer(data=request.data)
        print(request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        print("s",serializer.validated_data)
        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]

        
        result = verify_otp(email, otp)
        
        if result == "Verified":
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response(
                    {"message": "User not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            refresh = RefreshToken.for_user(user)
            response= Response({
                "message": "Email verified successfully",
                "user":{
                        "id": user.id,
                        "email": user.email,
                        "first_name": user.first_name,
                        "is_onboarded":user.is_onboarded,
                        "role":user.role
                    },
                "access": str(refresh.access_token),          
                }, status=status.HTTP_200_OK)
            response.set_cookie(
                key="refresh_token",
                value=str(refresh),
                httponly=True,
                secure=not settings.DEBUG,      
                samesite="Lax",  
                max_age=7 * 24 * 60 * 60  # 7 days
            )
            print(request.COOKIES.get("refresh_token"))
            return response

        return Response({"message": result}, status=status.HTTP_400_BAD_REQUEST)


class ResendOtpApi(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = ResendOtpSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data["email"]

        send_code_to_user(email)

        return Response({"message": "OTP sent successfully"}, status=status.HTTP_200_OK)


class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self,request):
        try:
            serializer=LoginSerializer(data=request.data)
            print(request.data)
            if serializer.is_valid():
                user=serializer.validated_data["user"]
                refresh = RefreshToken.for_user(user)
                response= Response({
                    "message":"Login successful",
                    "user":{
                        "id": user.id,
                        "email": user.email,
                        "first_name": user.first_name,
                        "is_onboarded":user.is_onboarded,
                        "is_superuser":user.is_superuser,
                        "role":user.role
                    },
                    "access": str(refresh.access_token),
                },status=status.HTTP_200_OK)
                response.set_cookie(
                    key="refresh_token",
                    value=str(refresh),
                    httponly=True,
                    secure=not settings.DEBUG,      
                    samesite="Lax",  
                    max_age=7 * 24 * 60 * 60  # 7 days
                )
                return response
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"message": "Something went wrong", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# onboarding       
class ProfileDataView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request):
        try:
            print(request.data)
            serializer=ProfiledataSerializer(instance=request.user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    "message":"Profile updated successfully"
                },status=status.HTTP_200_OK)
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"message": "Something went wrong", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class forgot_password_otpView(APIView):
    permission_classes=[AllowAny]
    def post(self,request):
        serializer=ResendOtpSerializer(data=request.data)
        if serializer.is_valid():
            email=serializer.validated_data["email"]
            if not User.objects.filter(email=email).exists():
                return Response(
                    {"message": "User with this email doesn't exist"},
                    status=status.HTTP_404_NOT_FOUND)
                
            send_code_to_user(email)
            return Response({"message": "OTP sent successfully"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# password verify otp
class PasswoVerifyOtpApi(APIView):
    permission_classes = [AllowAny]
    def post(self,request):
        serializer=OtpSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            otp = serializer.validated_data["otp"]
            result = Pass_verify_otp(email, otp)
            if result == "Verified":
                # ✅ Generate reset token
                reset_token = str(uuid.uuid4())

                # ✅ Store token → email (valid for 5 minutes)
                cache.set(
                    f"reset_token_{reset_token}",
                    email,
                    timeout=300
                )
                return Response(
                    {"message": "OTP verified successfully",
                     "reset_token": reset_token
                     },
                    status=status.HTTP_200_OK)
            return Response({"message":result}, status=status.HTTP_400_BAD_REQUEST)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
       
        

class PasswordChangeAPIView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        if serializer.is_valid():
            reset_token = serializer.validated_data["reset_token"]
            password = serializer.validated_data["password"]
            email = cache.get(f"reset_token_{reset_token}")

            if not email:
                return Response(
                    {"message": "Invalid or expired reset token"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response(
                    {"message": "User not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            user.set_password(password)
            user.save()
            cache.delete(f"reset_token_{reset_token}")
            return Response(
                {"message": "Password changed successfully"},
                status=status.HTTP_200_OK
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        print(refresh_token)
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()   
            except TokenError:
                pass
        response = Response(
            {"message": "Logged out successfully"},
            status=status.HTTP_200_OK
        )

        # ✅ Delete cookie
        response.delete_cookie("refresh_token")
        return response

# fetch current user
class GetUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user  # get current logged-in user
        serializer = UserSerializer(user)
        return Response(serializer.data)

# fetch all users
class GetAllUsersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        users = User.objects.filter(is_superuser=False)
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
    

class CreatePost(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request):
        serializer=PostSerializer(data=request.data)
        if serializer.is_valid():
            post=Post.objects.create(
                user=request.user,
                media_url=serializer.validated_data["media_url"],
                media_type=serializer.validated_data["media_type"],
                description=serializer.validated_data.get("description", "")
            )
            post.save()
            return Response({"message":"Post created successfully"},status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# presigned vie for mediafile upload
class GeneratePresignedURL(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_name = request.data["file_name"]
        file_type = request.data["file_type"]

        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )

        key = f"posts/{uuid.uuid4()}_{file_name}"

        upload_url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
                "Key": key,
                "ContentType": file_type,
            },
            ExpiresIn=3600,  
        )

        file_url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com/{key}"
        print(upload_url,"fffffFFfffff",file_url)
        return Response({
            "upload_url": upload_url,
            "file_url": file_url
        })

class GetUserpostView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        image_posts = Post.objects.filter(user=request.user,media_type="image").order_by("-created_at")
        video_posts = Post.objects.filter(user=request.user,media_type="video").order_by("-created_at")
        image_serializer = GetpostSerializer(image_posts, many=True)
        video_serializer=GetpostSerializer(video_posts, many=True)
        user_serializer = UserSerializer(request.user)
        return Response({
            "images": image_serializer.data,
            "videos": video_serializer.data,
            "user":user_serializer.data
        })

class GetpostView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        image_posts = Post.objects.filter(media_type="image").order_by("-created_at")
        video_posts = Post.objects.filter(media_type="video").order_by("-created_at")
        image_serializer = GetpostSerializer(image_posts, many=True)
        video_serializer=GetpostSerializer(video_posts, many=True)
        return Response({
            "images": image_serializer.data,
            "videos": video_serializer.data,
        })
    
class FollowView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FollowSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        follow, created = Follow.objects.get_or_create(
            follower=request.user,
            following=serializer.validated_data["following"]
        )

        if not created:
            return Response(
                {"error": "Already following this user"},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"message": "Followed successfully"},
            status=status.HTTP_201_CREATED
        )

    def delete(self, request):
        serializer = FollowSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        Follow.objects.filter(
            follower=request.user,
            following=serializer.validated_data["following"]
        ).delete()

        return Response(
            {"message": "Unfollowed successfully"},
            status=status.HTTP_200_OK
        )

class FollowStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.query_params.get("user_id")
        print("id",user_id)
        if not user_id:
            return Response(
                {"error": "user_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Is request.user following this user?
        is_following = Follow.objects.filter(
            follower=request.user,
            following=user_id
        ).exists()

        # How many followers this user has
        followers_count = Follow.objects.filter(
            following=user_id
        ).count()

        # How many users this user is following
        following_count = Follow.objects.filter(
            follower=user_id
        ).count()

        return Response({
            "is_following": is_following,
            "followers_count": followers_count,
            "following_count": following_count
        })







# **********************************************************AdminView************************************************


class BlockUserView(APIView):
    permission_classes = [IsAuthenticated]  

    def put(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = UserBlockSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)