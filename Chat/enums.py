from django.db.models import TextChoices


class FileType(TextChoices):
    TEXT = 'text', 'Text'
    IMAGE = 'image', 'Image'
    VIDEO = 'video', 'Video'
    DOCUMENT = 'docs', 'Document'
    AUDIO = 'audio', 'Audio'

class CategoryType(TextChoices):
    CHAT = 'chat', 'Chat'
    VIDEO = 'video', 'Video'