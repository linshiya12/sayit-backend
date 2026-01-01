from django.db import models
from django.contrib.auth.models import AbstractUser
from .manager import CustomUserManager
# Create your models here.


class Spokenlang(models.Model):
    spoken_language=models.CharField(max_length=50,unique=True)

    def __str__(self):
        return self.spoken_language
    
class User(AbstractUser):
    username = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(unique=True)
    prof_photo=models.ImageField(upload_to="profile_images/",default="profile_images/default-black.png",blank=True,null=True)
    is_verified=models.BooleanField(default=False)
    is_blocked=models.BooleanField(default=False)
    is_onboarded=models.BooleanField(default=False)
    role=models.CharField(max_length=50,blank=True, null=True)
    hourlyrate=models.IntegerField(blank=True, null=True)
    bio=models.TextField(blank=True, null=True)
    learning_language=models.CharField(max_length=50,blank=True, null=True)
    native_language=models.CharField(max_length=50,blank=True, null=True)
    spoken_languages=models.ManyToManyField("Spokenlang",blank=True)


    USERNAME_FIELD="email"
    REQUIRED_FIELDS=["first_name","last_name"]
    objects=CustomUserManager()
    def __str__(self):
        return str(self.id)
    

class Post(models.Model):
    user=models.ForeignKey('User', related_name='post', on_delete=models.CASCADE)
    media_url=models.URLField()
    media_type = models.CharField(max_length=10)
    comment_count=models.IntegerField(default=0)
    likes_count=models.IntegerField(default=0)
    reported_count=models.IntegerField(default=0)
    description=models.CharField(max_length=600,blank=True)
    created_at=models.DateField(auto_now_add=True)
    updated_at=models.DateField(auto_now=True)
    def __str__(self):
        return self.media_url

class PostReport(models.Model):
    user_id=models.ForeignKey('User', related_name='post_reported_user', on_delete=models.CASCADE)
    post_id=models.ForeignKey("Post", related_name='post_report', on_delete=models.CASCADE)
    Reason=models.CharField(max_length=50)
    def __str__(self):
        return self.post_id

class Likes(models.Model):
    user=models.ForeignKey('User', related_name='post_liked_user', on_delete=models.CASCADE)
    post=models.ForeignKey("Post", related_name='post_liked', on_delete=models.CASCADE)
    class Meta:
        unique_together = ('user', 'post')
    def __str__(self):
        return self.post_id

class Comments(models.Model):
    user_id=models.ForeignKey("User", related_name='comments', on_delete=models.CASCADE)
    post_id=models.ForeignKey("Post", related_name='commented_post', on_delete=models.CASCADE)
    content=models.CharField(max_length=500)
    created_at=models.DateField(auto_now_add=True)
    def __str__(self):
        return self.content

class Follow(models.Model):
    follower=models.ForeignKey('User', related_name='follower', on_delete=models.CASCADE)
    following=models.ForeignKey('User', related_name='following', on_delete=models.CASCADE)
    class Meta:
        unique_together = ('follower', 'following')

    def __str__(self):
        return f"{self.follower} follows {self.following}"