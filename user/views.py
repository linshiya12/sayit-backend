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
from google.oauth2 import id_token
from google.auth.transport import requests
from django.shortcuts import get_object_or_404
import logging


logger = logging.getLogger(__name__)

class HomeView(APIView):
    def get(self, request):
        return Response({"message": "hello"})
    
class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.COOKIES.get("refresh_token")
            logger.info(f"refresh token: {refresh_token}")
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
                if user.is_blocked:
                    return Response(
                        {"message": "Your account is blocked. Please contact support."},
                        status=status.HTTP_403_FORBIDDEN
                    )
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
    

# googleauthentication
class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("token")

        if not token:
            return Response(
                {"error": "Token is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Verify token with Google
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                settings.GOOGLE_OAUTH_CLIENT_ID
            )
            email = idinfo.get("email")
            first_name = idinfo.get("given_name", "")
            last_name = idinfo.get("family_name", "")

        except ValueError:
            return Response(
                {"error": "Invalid Google token"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 🔑 EMAIL = IDENTITY
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "username": email.split("@")[0],
                "is_verified" : True
            }
        )

        # OPTIONAL: mark as google user
        if created:
            user.set_unusable_password()
            user.save()

        refresh = RefreshToken.for_user(user)
        response= Response({
            "message": "Login successful",
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
        return response
        

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

# fetch and edit current user
class GetUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logger.info("name")
        user = request.user  # get current logged-in user
        serializer = UserSerializer(user)
        return Response(serializer.data)
    def put(self, request):
        print(request.data)
        serializer = UserSerializer(
            request.user,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()
            return Response({"updated_user":serializer.data})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
        folder = request.data["folder"]

        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )

        key = f"{folder}/{uuid.uuid4()}_{file_name}"

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
    def get(self, request, id):
        print("hi")
        user = get_object_or_404(User, id=id)
        image_posts = Post.objects.filter(user=user,media_type="image").order_by("-created_at")
        video_posts = Post.objects.filter(user=user,media_type="video").order_by("-created_at")
        image_serializer = GetpostSerializer(image_posts, many=True)
        video_serializer=GetpostSerializer(video_posts, many=True)
        user_serializer = UserSerializer(user)
        return Response({
            "images": image_serializer.data,
            "videos": video_serializer.data,
            "user":user_serializer.data
        })

class GetOwnpostView(APIView):
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

class GetGlobalPostView(APIView):
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
            following=serializer.validated_data["following"],
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

class CommentView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request):
        print(request.user.id)
        serializer=CommentSerializer(data=request.data)
        if serializer.is_valid():
            comment=Comments.objects.create(
                user_id=request.user,
                post_id=serializer.validated_data["post_id"],
                content=serializer.validated_data["content"]
            )
            return Response({"message":"Comment added successfully"},status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 
    def get(self, request):
        post_id = request.query_params.get("post_id")

        if not post_id:
            return Response(
                {"message": "post_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        comments = Comments.objects.filter(post_id=post_id)
        serializer = CommentSerializer(comments, many=True)

        return Response(
            {"comments": serializer.data},
            status=status.HTTP_200_OK
        )

    def delete(self,request):
        comment_id = request.query_params.get("comment_id")

        if not comment_id:
            return Response(
                {"message": "comment_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            comment = Comments.objects.get(id=comment_id,user_id=request.user)
            comment.delete()
            return Response(
                {"message": "Comment deleted"},
                status=status.HTTP_204_NO_CONTENT
            )
        except Comments.DoesNotExist:
            return Response(
                {"message": "Comment not found or not authorized"},
                status=status.HTTP_404_NOT_FOUND
            )
class DeleteOwnPostComment(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        comment_id = request.query_params.get("comment_id")
        if not comment_id:
            return Response(
                {"message": "comment_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        deleted, _ = Comments.objects.filter(
            id=comment_id,
            post_id__user=request.user.id
        ).delete()

        if deleted == 0:
            return Response(
                {"message": "Comment not found or not authorized"},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response(
            {"message": "Comment deleted"},
            status=status.HTTP_204_NO_CONTENT
        )

class ReportedView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request):
        serializer=PostSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user_id=request.user.id)
            return Response(
                {"message":"Post reported successfully"},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 

class PostLikesView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request):
        serializer=LikesSerializer(data=request.data,context={"request": request})
        if serializer.is_valid():
            print(serializer.validated_data)
            like=Likes.objects.filter(user=request.user,post=serializer.validated_data["post"]).first()
            if like:
                like.is_liked=True
                like.save()
            else:
                Likes.objects.create(user=request.user,post=serializer.validated_data["post"],is_liked=True)
            return Response(
                {"message":"liked successfully"},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 
    def get(self,request,id):
        total_likes=Likes.objects.filter(post__id=id,is_liked=True).count()
        if Likes.objects.filter(post__id=id,is_liked=True,user=request.user).exists():
            is_liked=True
        else:
            is_liked=False
        print(total_likes,is_liked)
        return Response(
            {"total_likes":total_likes, "is_liked":is_liked},
            status=status.HTTP_200_OK
        )

    def put(self, request):
        post_id = request.query_params.get("post")

        if not post_id:
            return Response(
                {"message": "post is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            like = Likes.objects.get(user=request.user, post_id=post_id)
            like.is_liked = False
            like.save()

            return Response(
                {"message": "Like removed"},
                status=status.HTTP_200_OK
            )

        except Likes.DoesNotExist:
            return Response(
                {"message": "Like does not exist"},
                status=status.HTTP_404_NOT_FOUND
            )

        
class ReviewView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request):
        serializer=RatingSerializer(data=request.data,context={"request": request})
        if serializer.is_valid():
            student_id=request.user
            if student_id==serializer.validated_data["mentor"]:
                return Response(
                    {"message":"You cannot rate yourself"},
                    status=status.HTTP_403_FORBIDDEN
                )
            serializer.save(student=request.user)
            return Response(
                {"message": "Review submitted successfully"},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 
    def get(self,request):
        mentorId=request.query_params.get("mentor_id")
        if not mentorId:
            return Response(
                {"message": "mentor_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        reviews=MentorRating.objects.filter(mentor=mentorId)
        serializer = RatingSerializer(reviews, many=True)
        return Response(
            {
                "reviews":serializer.data
            },
            status=status.HTTP_200_OK
        )
    def delete(self,request):
        review_id=request.query_params.get("id")
        if not review_id:
            return Response(
                {"message": "review_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            ) 

        
        review=get_object_or_404(MentorRating,id=review_id)
        if review.mentor != request.user:
            return Response(
                {"message": "You are not allowed to delete this review"},
                status=status.HTTP_403_FORBIDDEN
            )
        review.delete()
        return Response(
            {"message":"review deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )








        






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
    
class GetAllpostView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        posts = Post.objects.all().order_by("-created_at")
        serializer=GetpostSerializer(posts, many=True)
        return Response({
            "posts": serializer.data,
        })