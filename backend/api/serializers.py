from django.contrib.auth import get_user_model
from django.db import transaction
from django.forms import ValidationError
from djoser.serializers import UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from api.constants import LIMIT_SIZE
from recipes.constants import INGREDIENT_AMOUNT_MAX, INGREDIENT_AMOUNT_MIN
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from users.models import Follow

User = get_user_model()


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(allow_null=True)

    class Meta:
        model = User
        fields = ('avatar',)


class GramUserSerializer(UserSerializer):
    avatar = Base64ImageField(required=False, allow_null=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        model = User
        fields = UserSerializer.Meta.fields + (
            'password',
            'avatar',
            'is_subscribed'
        )
        read_only_fields = ('id', 'is_subscribed')

    def get_is_subscribed(self, obj):
        request = self.context['request']
        return (request and request.user.is_authenticated
                and request.user.subscriptions_client.filter(
                    author=obj).exists())


class ShortRecipeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class FavoriteShoppingCartSerializers(serializers.ModelSerializer):

    class Meta:
        fields = ('recipe', 'user')

    def validate(self, data):
        user = data.get('user')
        recipe = data.get('recipe')
        if self.Meta.model.objects.filter(recipe=recipe, user=user).exists():
            raise ValidationError(
                f'"{recipe.name}" уже добавлен в {self._meta.verbose_name}')
        return data

    def to_representation(self, instance):
        return ShortRecipeSerializer(
            instance.recipe,
            context=self.context
        ).data


class FavoriteSerializer(FavoriteShoppingCartSerializers):

    class Meta(FavoriteShoppingCartSerializers.Meta):
        model = Favorite


class FollowCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Follow
        fields = ('user', 'author')

    def to_representation(self, instance):
        serializer = FollowIssuanceSerializer(
            instance.author,
            context=self.context
        )
        return serializer.data

    def validate(self, data):
        user = data.get('user')
        author = data.get('author')
        if user == author:
            raise ValidationError(
                {'errors': ('Нельзя подписаться на самого себя.')},
            )
        if Follow.objects.filter(user=user, author=author).exists():
            raise ValidationError(
                {'errors': 'Вы уже подписаны на этого пользователя.'},
            )
        return data


class FollowIssuanceSerializer(GramUserSerializer):
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(default=0)

    class Meta(GramUserSerializer.Meta):
        model = User
        fields = GramUserSerializer.Meta.fields + (
            'recipes_count',
            'avatar',
            'is_subscribed',
            'recipes',
        )
        read_only_fields = (
            'username',
            'email',
            'first_name',
            'last_name',
            'id'
        )

    def get_recipes(self, obj):
        request = self.context['request']
        if 'recipes_limit' in request.GET:
            try:
                limit = int(request.GET['recipes_limit'])
            except ValueError:
                pass
        else:
            limit = LIMIT_SIZE

        return ShortRecipeSerializer(
            obj.recipes.all()[:int(limit)],
            many=True,
            context=self.context
        ).data


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class RecipeIngredientCreateSerializer(serializers.ModelSerializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all(),
                                            source='ingredient.id')
    amount = serializers.IntegerField(
        max_value=INGREDIENT_AMOUNT_MAX,
        min_value=INGREDIENT_AMOUNT_MIN,
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeCreateSerializer(serializers.ModelSerializer):
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        label='Теги',
    )
    ingredients = RecipeIngredientCreateSerializer(
        many=True,
        label='Ингредиенты',
    )
    image = Base64ImageField(
        allow_null=True,
        label='Изображения'
    )

    class Meta:
        model = Recipe
        fields = (
            'cooking_time',
            'image',
            'ingredients',
            'name',
            'tags',
            'text',
        )

    @staticmethod
    def set_ingredients(ingredients, recipe):
        RecipeIngredient.objects.bulk_create(
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient['ingredient']['id'],
                amount=ingredient['amount']
            ) for ingredient in ingredients
        )

    def to_representation(self, instance):
        serializer = RecipeSerializer(
            instance,
            context=self.context
        )
        return serializer.data

    @transaction.atomic
    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients', None)
        tags = validated_data.pop('tags')
        user = self.context.get('request').user
        recipe = Recipe.objects.create(**validated_data, author=user)
        recipe.tags.set(tags)
        self.set_ingredients(ingredients, recipe)
        return recipe

    def update(self, instance, validated_data):
        instance.tags.clear()
        instance.ingredients.clear()
        self.set_ingredients(validated_data.pop('ingredients'), instance)
        instance.tags.set(validated_data.pop('tags'))
        return super().update(instance, validated_data)

    def validate(self, data):
        ingredients = data.get('ingredients')
        tags = data.get('tags')
        if not ingredients:
            raise serializers.ValidationError({
                'ingredients': 'Добавьте хоть 1 ингредиент.'})
        if not tags:
            raise serializers.ValidationError({
                'tags': 'Добавьте тег.'})
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError('Теги дублируются.')
        ingredient_list = [ingredient['ingredient'][
            'id'] for ingredient in ingredients]
        if len(ingredient_list) != len(set(ingredient_list)):
            raise serializers.ValidationError('Ингредиенты дублируются.')
        return data


class RecipeSerializer(serializers.ModelSerializer):
    author = GramUserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='ingredient_list',
        many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    tags = TagSerializer(many=True)

    class Meta:
        model = Recipe
        fields = (
            'author',
            'cooking_time',
            'id',
            'image',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'tags',
            'text',
        )

    def check_request(self, obj, model):
        request = self.context.get('request')
        return (
            request
            and request.user.is_authenticated
            and model.objects.filter(recipe=obj.id, user=request.user).exists()
        )

    def get_is_favorited(self, obj):
        return self.check_request(obj, Favorite)

    def get_is_in_shopping_cart(self, obj):
        return self.check_request(obj, ShoppingCart)


class ShoppingCartSerializer(FavoriteShoppingCartSerializers):

    class Meta(FavoriteShoppingCartSerializers.Meta):
        model = ShoppingCart
