from django.contrib import admin
from django.urls import path
from .views import *

urlpatterns = [
    path('get-or-createchatroom/<int:id>/',get_create_chatroom.as_view(),name="getorcreatechatroom"),
    path('list-chatroom/',list_chatroom.as_view(),name="listchatroom"),
    path('get-chat/<str:room_name>/',get_message.as_view(),name="getchat")
]