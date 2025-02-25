from django_filters.rest_framework import FilterSet, filters

from recipes.models import Ingredient, Recipe, Tag


class IngredientFilter(FilterSet):
    name = filters.CharFilter(lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ('name',)


class RecipeFilter(FilterSet):
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all(),
        label='Теги'
    )
    is_favorited = filters.BooleanFilter(method='filter_is_favorited',
                                         label='Избранные')
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart',
        label='В списке покупок'
    )

    class Meta:
        model = Recipe
        fields = ('author', 'is_favorited', 'is_in_shopping_cart', 'tags')

    def filter_is_favorited(self, queryset, name, value):
        if self.request.user.is_authenticated and value:
            return queryset.filter(favorites__user=self.request.user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        if self.request.user.is_authenticated and value:
            return queryset.filter(shopping_carts__user=self.request.user)
        return queryset
