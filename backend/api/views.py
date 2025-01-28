from api.filters import IngredientFilter, RecipeFilter
from api.pagination import LimitPagination
from api.permissions import OwnerOrReadOnly
from api.serializers import (AvatarSerializer, FavoriteSerializer,
                             FollowCreateSerializer, FollowSerializer,
                             GramUserCreateSerializer, IngredientSerializer,
                             RecipeCreateSerializer, RecipeSerializer,
                             ShoppingCartSerializer, TagSerializer)
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse
from users.models import Follow

User = get_user_model()


@require_GET
def short_url(request, pk):
    get_object_or_404(Recipe, pk=pk)
    url = reverse('recipes', args=[pk])
    return redirect(url)


class GramUserViewSet(UserViewSet):
    queryset = User.objects.all()
    pagination_class = LimitPagination
    permission_classes = (AllowAny,)
    serializer_class = GramUserCreateSerializer

    @action(
        methods=['put'],
        detail=False,
        permission_classes=(IsAuthenticated, OwnerOrReadOnly),
        url_path='me/avatar',
    )
    def avatar(self, request):
        serializer = AvatarSerializer(
            instance=request.user,
            data=request.data,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @avatar.mapping.delete
    def delete_avatar(self, request, *args, **kwargs):
        self.request.user.avatar.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['get'],
        detail=False,
        permission_classes=(IsAuthenticated,)
    )
    def me(self, request, *args, **kwargs):
        self.get_object = self.get_instance
        return self.retrieve(request, *args, **kwargs)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=(IsAuthenticated,)
    )
    def subscribe(self, request, id):
        user = request.user
        subscriber = get_object_or_404(User, id=id)
        if user == subscriber:
            return Response(
                {'errors': ('Нельзя подписаться на самого себя.')},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if Follow.objects.filter(user=user, subscriber=subscriber).exists():
            return Response(
                {'errors': 'Вы уже подписаны на этого пользователя.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = FollowCreateSerializer(
            context={'request': request},
            data={
                'subscriber': subscriber.id,
                'user': user.id
            }
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        users_annotated = User.objects.annotate(
            recipes_count=Count('recipes'))
        subscriber_annotated = users_annotated.filter(id=id).first()
        serializer = FollowSerializer(
            subscriber_annotated,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscribe(self, request, id):
        user = request.user
        subscriber = get_object_or_404(User, id=id)
        delete_subscriber, _ = (
            Follow.objects.filter(user=user, subscriber=subscriber).delete()
        )
        if delete_subscriber:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'detail': 'Вы не подписаны на этого пользователя.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=False,
        methods=['get'],
        permission_classes=(IsAuthenticated,),
        url_name='subscriptions',
        url_path='subscriptions',
    )
    def get_subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(follow__user=user).annotate(
            recipes_count=Count('recipes')
        )
        pages = self.paginate_queryset(queryset)
        serializer = FollowSerializer(
            pages,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    permission_classes = (AllowAny,)
    serializer_class = IngredientSerializer


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = (
        Recipe.objects
        .select_related('author')
        .prefetch_related('ingredients', 'tags')
    )
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter
    pagination_class = LimitPagination
    permission_classes = (OwnerOrReadOnly,)

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve', 'get-link'):
            return RecipeSerializer
        return RecipeCreateSerializer

    @action(
        detail=False,
        methods=['get'],
        permission_classes=(IsAuthenticated,),
        url_path='download_shopping_cart',
        url_name='download_shopping_cart',
    )
    def download_shopping_cart(self, request):
        ingredients = (
            RecipeIngredient.objects.filter(
                recipe__shopping_cart__user=request.user)
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(sum=Sum('amount'))
        )
        shopping_cart = self.shopping_cart_in_file(ingredients)
        return HttpResponse(shopping_cart, content_type='text/plain')

    @action(
        detail=True,
        methods=['get'],
        permission_classes=(AllowAny,),
        url_path='get-link',
        url_name='get-link',
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        short_link = reverse('short_url', args=[recipe.pk])
        return Response({'short-link': request.build_absolute_uri(short_link)},
                        status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=(IsAuthenticated,),
        url_path='favorite',
        url_name='favorite',
    )
    def favorite(self, request, pk):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        if Favorite.objects.filter(recipe=recipe, user=user).exists():
            return Response(
                {'detail': (f'"{recipe.name}" уже добавлен в избранное')},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = FavoriteSerializer(
            data={
                'recipe': recipe,
                'user': user
            }
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(recipe=recipe, user=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        deleted_objects_number, _ = (
            Favorite.objects.filter(recipe=recipe, user=user).delete()
        )
        if deleted_objects_number:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'detail': 'Рецепта нет в избранных.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=True,
        methods=['post'],
        permission_classes=(IsAuthenticated,),
        url_path='shopping_cart',
        url_name='shopping_cart',
    )
    def shopping_cart(self, request, pk):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        if ShoppingCart.objects.filter(recipe=recipe, user=user).exists():
            return Response(
                {'detail': f'"{recipe.name}" уже в списке покупок'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = ShoppingCartSerializer(
            data={
                'recipe': recipe,
                'user': user
            }
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(recipe=recipe, user=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk):
        user = request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        deleted_object, _ = (
            ShoppingCart.objects.filter(recipe=recipe, user=user).delete()
        )
        if deleted_object:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'detail': 'Рецепта нет в списке покупок.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @staticmethod
    def shopping_cart_in_file(ingredients):
        return '\n'.join(
            f'{ingredient["ingredient__name"]} - {ingredient["sum"]} '
            f'({ingredient["ingredient__measurement_unit"]})'
            for ingredient in ingredients
        )


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (OwnerOrReadOnly,)
