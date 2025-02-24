from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group

from recipes.models import Recipe
from users.models import Follow

user = get_user_model()


@admin.register(user)
class GramUserAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'email',
                    'is_staff', 'recipes_count', 'follow_count')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email')

    @admin.display(description='Кол-во рецептов')
    def recipes_count(self, obj):
        return Recipe.objects.filter(author=obj).count()

    @admin.display(description='Кол-во подписчиков')
    def follow_count(self, obj):
        return Follow.objects.filter(author=obj).count()


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('user', 'author')
    search_fields = (
        'user__username',
        'author__username'
    )


admin.site.unregister(Group)
