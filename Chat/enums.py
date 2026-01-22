from django.db.models import TextChoices





class RoomType(TextChoices):
    INDIVIDUAL = 'Individual'
    GROUP = 'group'


class FileType(TextChoices):
    TEXT = 'text', 'Text'
    IMAGE = 'image', 'Image'
    VIDEO = 'video', 'Video'
    DOCUMENT = 'docs', 'Document'
    AUDIO = 'audio', 'Audio'