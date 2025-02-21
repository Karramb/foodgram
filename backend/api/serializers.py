from api.constants import LIMIT_SIZE
from django.contrib.auth import get_user_model
from django.forms import ValidationError
from djoser.serializers import UserSerializer
from drf_extra_fields.fields import Base64ImageField
from recipes.constants import INGREDIENT_AMOUNT_MAX, INGREDIENT_AMOUNT_MIN
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from rest_framework import serializers
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
        return (request and request.user
                and request.user.follow.filter(author=obj).exists())


class FavoriteSerializer(serializers.ModelSerializer):
    recipe = serializers.ReadOnlyField(source='recipe.id')
    user = serializers.ReadOnlyField(source='user.id')

    class Meta:
        model = Favorite
        fields = ('recipe', 'user')

    def validate(self, data):
        user = data.get('user')
        recipe = data.get('recipe')
        if Favorite.objects.filter(recipe=recipe, user=user).exists():
            raise ValidationError(
                f'"{recipe.name}" уже добавлен в избранное')
        return data

    def to_representation(self, instance):
        return ShortRecipeSerializer(
            instance.recipe,
            context=self.context
        ).data


class FollowCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Follow
        fields = ('user', 'author')

    def to_representation(self, instance):
        serializer = FollowIssuanceSerializer(
            instance,
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


class FollowIssuanceSerializer(UserSerializer):
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField()

    class Meta(UserSerializer.Meta):
        model = User
        fields = UserSerializer.Meta.fields + (
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

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        return user.subscriber.exists()

    def get_recipes(self, obj):
        request = self.context['request']
        if "recipes_limit" in request.GET:
            try:
                limit = int(request.GET["recipes_limit"])
            except ValueError:
                print('Лимит не является числом')
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

    def set_ingredients(self, ingredients, recipe):
        ingredients_set = []
        for ingredient in ingredients:
            recipe_ingredient = RecipeIngredient(
                ingredient=ingredient['ingredient']['id'],
                recipe=recipe,
                amount=ingredient['amount']
            )
            ingredients_set.append(recipe_ingredient)
        RecipeIngredient.objects.bulk_create(ingredients_set)

    def to_representation(self, instance):
        serializer = RecipeSerializer(
            instance,
            context=self.context
        )
        return serializer.data

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
        if len(ingredients) != len(set(ingredients)):
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


class ShoppingCartSerializer(FavoriteSerializer):

    class Meta(FavoriteSerializer.Meta):
        model = ShoppingCart

    def validate(self, data):
        user = data.get('user')
        recipe = data.get('recipe')
        if ShoppingCart.objects.filter(recipe=recipe, user=user).exists():
            raise ValidationError(f'"{recipe.name}" уже в списке покупок')
        return data


class ShortRecipeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
