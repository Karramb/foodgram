from django.contrib.auth.models import AbstractUser
from django.db import models
from django.forms import ValidationError

from users.constants import MAX_LENGTH_FOR_EMAIL, MAX_LENGTH_FOR_FIELDS
from users.validators import validate_username


class GramUser(AbstractUser):
    REQUIRED_FIELDS = (
        'first_name',
        'last_name',
        'username',
    )
    USERNAME_FIELD = 'email'

    username = models.CharField(
        max_length=MAX_LENGTH_FOR_FIELDS,
        unique=True,
        validators=(validate_username,),
        verbose_name='Никнейм'
    )
    email = models.EmailField(
        max_length=MAX_LENGTH_FOR_EMAIL,
        unique=True,
        verbose_name='email'
    )
    first_name = models.CharField(
        max_length=MAX_LENGTH_FOR_FIELDS,
        verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=MAX_LENGTH_FOR_FIELDS,
        verbose_name='Фамилия'
    )
    avatar = models.ImageField(
        blank=True,
        null=True,
        verbose_name='Фото профиля',
        upload_to='media/users_avatars/'
    )

    class Meta:
        ordering = ('username',)
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


class Follow(models.Model):
    user = models.ForeignKey(
        GramUser,
        on_delete=models.CASCADE,
        related_name='user_subscriptions',
        verbose_name='Пользователь',
    )
    author = models.ForeignKey(
        GramUser,
        on_delete=models.CASCADE,
        related_name='subscriptions_to_author',
        verbose_name='Автор',
    )

    class Meta:
        ordering = ('user',)
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'author'),
                name='unique subscribe'
            ),
        )

    def __str__(self):
        return f'{self.user} подписан на {self.author}'

    def clean(self):
        if self.user == self.author:
            raise ValidationError(
                'Вы не можете подписаться на самого себя ')
