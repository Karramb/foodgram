from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from recipes.constants import (COOKING_TIME_MAX, COOKING_TIME_MIN,
                               INGREDIENT_AMOUNT_MAX, INGREDIENT_AMOUNT_MIN,
                               MAX_LEN_STR_DEF, MAX_LENGTH_INGREDIENT_NAME,
                               MAX_LENGTH_MEASUREMENT_UNIT,
                               MAX_LENGTH_RECIPE_NAME, MAX_LENGTH_TAG)

User = get_user_model()


class Tag(models.Model):
    name = models.CharField(
        max_length=MAX_LENGTH_TAG,
        unique=True,
        verbose_name='Название'
    )
    slug = models.CharField(
        max_length=MAX_LENGTH_TAG,
        unique=True,
        verbose_name='Короткая ссылка'
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name[:MAX_LEN_STR_DEF]


class Ingredient(models.Model):
    name = models.CharField(
        max_length=MAX_LENGTH_INGREDIENT_NAME,
        verbose_name='Название'
    )
    measurement_unit = models.CharField(
        max_length=MAX_LENGTH_MEASUREMENT_UNIT,
        verbose_name='Единица измерения'
    )

    class Meta:
        ordering = ('name',)
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Ингредиенты'
        constraints = (
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='Проверка названия и веса',
            ),
        )

    def __str__(self):
        return self.name[:MAX_LEN_STR_DEF]


class Recipe(models.Model):
    name = models.CharField(
        'Название', max_length=MAX_LENGTH_RECIPE_NAME,
    )
    tags = models.ManyToManyField(
        Tag, verbose_name='Тег'
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='RecipeIngredient',
        verbose_name='Ингредиенты'
    )
    text = models.TextField(
        'Текст',)
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    cooking_time = models.PositiveSmallIntegerField(
        'Время готовки',
        validators=(
            MinValueValidator(COOKING_TIME_MIN),
            MaxValueValidator(COOKING_TIME_MAX),
        )
    )
    image = models.ImageField(
        'Изображение', upload_to='media/recipes_images/'
    )
    pub_date = models.DateTimeField(
        'Дата публикации', auto_now_add=True
    )

    class Meta:
        ordering = ('-pub_date',)
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name[:MAX_LEN_STR_DEF]


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredient_list',
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.RESTRICT,
        related_name='ingredient',
        verbose_name='ингредиент'
    )
    amount = models.PositiveSmallIntegerField(
        validators=(
            MinValueValidator(
                INGREDIENT_AMOUNT_MIN,
                message=(f'Минимальное количество - '
                         f'{INGREDIENT_AMOUNT_MIN} !')
            ),
            MaxValueValidator(
                INGREDIENT_AMOUNT_MAX,
                message=(f'Максимальное количество - '
                         f'{INGREDIENT_AMOUNT_MAX} !')
            ),
        ),
        verbose_name='Количество',
    )

    class Meta:
        ordering = ('recipe',)
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Количество ингредиентов'
        constraints = (
            models.UniqueConstraint(
                fields=('ingredient', 'recipe'),
                name='unique_ingredient_in_recipe',
            ),
        )

    def __str__(self):
        return f'"{self.recipe}" содержит {self.ingredient}"'


class ShoppingCartFavorite(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )

    @property
    def name_model(self):
        return self.__class__.__name__

    class Meta:
        abstract = True
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique recipe in %(class)s'),
        )

    def __str__(self):
        return (f'"{self.recipe}" добавлен в "{self._meta.verbose_name}" у '
                f'"{self.user}"')


class ShoppingCart(ShoppingCartFavorite):
    class Meta(ShoppingCartFavorite.Meta):
        default_related_name = 'shopping_cart'
        verbose_name = 'список покупок'
        verbose_name_plural = 'Списки покупок'


class Favorite(ShoppingCartFavorite):

    class Meta(ShoppingCartFavorite.Meta):
        default_related_name = 'favorite'
        verbose_name = 'избранное'
        verbose_name_plural = 'Избранное'
