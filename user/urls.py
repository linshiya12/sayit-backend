from django.contrib import admin
from django.urls import path
from .views import *

urlpatterns = [
    path('home/', HomeView.as_view()),
    path('api/auth/signup/',RegisterApi.as_view(),name="register"),
    path('api/auth/verify_otp/',VerifyOtpApi.as_view(),name="verify_otp"),
    path('api/auth/resend_otp/',ResendOtpApi.as_view(),name="resend_otp"),
    path('api/auth/login/',LoginView.as_view(),name="login"),
    path('api/auth/forgot_password_otp/',forgot_password_otpView.as_view(),name="forgot_password_otp"),
    path('api/auth/Passwo_verifyOtp/',PasswoVerifyOtpApi.as_view(),name="PasswoVerifyOtp"),
    path('api/auth/Password_Change/',PasswordChangeAPIView.as_view(),name="Password_Change"),
    path('api/onboarding/',ProfileDataView.as_view(),name="onboard"),
    path('api/auth/logout/',LogoutAPIView.as_view(),name="logout"),
    path('api/auth/currentuser',GetUserView.as_view(),name="currentuser"),
    path('api/admin/block-user/<int:user_id>/', BlockUserView.as_view(), name='block-user'),
    path('api/createpost/',CreatePost.as_view(),name="createpost"),
    path('api/getuserpost/',GetUserpostView.as_view(),name="getuserpost"),
    path('api/s3/presignedurl/',GeneratePresignedURL.as_view(),name="presignedurl"),
    path('api/getpost/',GetpostView.as_view(),name="getpost"),
    path('api/follow/',FollowView.as_view(),name="follow"),
    path('api/getfollow/',FollowStatusView.as_view(),name="getfollow"),

    # admin
    path('api/admin/users',GetAllUsersView.as_view(),name="alluser"),
]