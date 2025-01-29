import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer, UserSerializer
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from rest_framework import serializers
from users.constants import MAX_LENGTH_FOR_FIELDS
from users.models import Follow

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(allow_null=True)

    class Meta:
        model = User
        fields = ('avatar',)


class GramUserCreateSerializer(UserCreateSerializer):
    password = serializers.CharField(
        max_length=MAX_LENGTH_FOR_FIELDS,
        write_only=True
    )

    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'first_name',
            'last_name',
            'password',
            'id',
            'is_subscribed'
        )


class GramUserSerializer(UserSerializer):
    avatar = Base64ImageField(required=False, allow_null=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'first_name',
            'last_name',
            'password',
            'id',
            'avatar',
            'is_subscribed'
        )
        read_only_fields = ('id', 'is_subscribed')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            return False
        return request.user.follow.filter(author=obj).exists()


class FavoriteSerializer(serializers.ModelSerializer):
    recipe = serializers.ReadOnlyField(source='recipe.id')
    user = serializers.ReadOnlyField(source='user.id')

    class Meta:
        model = Favorite
        fields = ('recipe', 'user')

    def to_representation(self, instance):
        return ShortRecipeSerializer(
            instance.recipe,
            context={'request': self.context.get('request')}
        ).data


class FollowCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Follow
        fields = ('user', 'author')


class FollowSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField()

    class Meta:
        model = User
        fields = (
            'username',
            'email',
            'first_name',
            'last_name',
            'id',
            'avatar',
            'is_subscribed',
            'recipes',
            'recipes_count'
        )
        read_only_fields = (
            'username',
            'email',
            'first_name',
            'last_name',
            'id'
        )

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        return user.subscriber.exists()

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit', 6)
        return ShortRecipeSerializer(
            Recipe.objects.filter(author=obj)[:int(limit)],
            many=True,
            context={'request': request},
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
    id = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class RecipeIngredienSerializer(serializers.ModelSerializer):
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
        allow_empty=False,
        label='Ингридиенты',
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

    def set_ingredients(self, ingredients, recipe):
        ingredients_set = []
        for ingredient in ingredients:
            ingredient_id = ingredient['id']
            ingredient_in_obj = get_object_or_404(Ingredient, pk=ingredient_id)
            amount = ingredient['amount']
            recipe_ingredient = RecipeIngredient(
                ingredient=ingredient_in_obj, recipe=recipe, amount=amount
            )
            ingredients_set.append(recipe_ingredient)
        RecipeIngredient.objects.bulk_create(ingredients_set)

    def to_representation(self, instance):
        serializer = RecipeSerializer(
            instance,
            context={'request': self.context.get('request')}
        )
        return serializer.data

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients', None)
        if ingredients is None or len(ingredients) == 0:
            raise serializers.ValidationError({
                'ingredients': 'Добавьте ингредиент.'})
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
                'ingredients': 'Добавьте ингредиент.'})
        if not tags:
            raise serializers.ValidationError({
                'tags': 'Добавьте тег.'})
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError('Теги дублируются.')
        ingredients_ids = [ingredient['id'] for ingredient in ingredients]
        exist_ingredient = Ingredient.objects.filter(
            id__in=ingredients_ids)
        if exist_ingredient.count() != len(ingredients_ids):
            lost_id = set(ingredients_ids) - set(
                exist_ingredient.values_list('id', flat=True)
            )
            raise serializers.ValidationError(
                f'Ингредиент "{lost_id}" не существует.'
            )
        return data

    def validate_ingredients(self, value):
        if value is None:
            raise serializers.ValidationError('Добавьте ингридиенты')


class RecipeSerializer(serializers.ModelSerializer):
    author = GramUserSerializer(read_only=True)
    ingredients = RecipeIngredienSerializer(
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


class ShoppingCartSerializer(FavoriteSerializer):

    class Meta(FavoriteSerializer.Meta):
        model = ShoppingCart


class ShortRecipeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
