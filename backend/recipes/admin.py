from django.contrib import admin
from django.db.models import Count
from django.utils.safestring import mark_safe

from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)


class RecipeIngredientInLine(admin.TabularInline):
    model = RecipeIngredient
    extra = 0
    min_num = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'name',
        'cooking_time',
        'author',
        'added_in_favorite',
        'get_ingredients',
        'get_tags',
        'mini_image'
    )
    search_fields = (
        'author__username',
        'name'
    )
    list_filter = ('tags',)
    filter_horizontal = ('tags',)
    inlines = (RecipeIngredientInLine,)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(added_in_favorite=Count('favorite'))
        return queryset

    @admin.display(description='Ингредиенты')
    def get_ingredients(self, obj):
        return ",\n".join(str(p) for p in obj.ingredients.all())

    @admin.display(description='Тэги')
    def get_tags(self, obj):
        return ",\n".join(str(p) for p in obj.tags.all())

    @admin.display(description='В избранном')
    def added_in_favorite(self, obj):
        return obj.added_in_favorite

    @admin.display(description='В избранном')
    def mini_image(self, obj):
        return mark_safe(f'<img src={obj.image.url} width="80" height="60">')

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'slug'
    )
    search_fields = (
        'name',
    )


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'measurement_unit'
    )
    search_fields = (
        'name',
    )


@admin.register(Favorite, ShoppingCart)
class FavoriteAndShoppingCartAdmin(admin.ModelAdmin):
    search_fields = (
        'user__username',
        'recipe__name'
    )
