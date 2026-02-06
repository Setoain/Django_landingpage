from django.db import models
from django.core.validators import EmailValidator

class Email(models.Model):
    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
        max_length=255
    )

    class Meta:
        db_table = 'waitlist'
        managed = True

    def __str__(self):
        return self.email
