from api.filters import IngredientFilter, RecipeFilter
from api.pagination import LimitPagination
from api.permissions import OwnerOrReadOnly
from api.serializers import (AvatarSerializer, FavoriteSerializer,
                             FollowCreateSerializer, FollowSerializer,
                             GramUserSerializer, IngredientSerializer,
                             RecipeCreateSerializer, RecipeSerializer,
                             ShoppingCartSerializer, TagSerializer)
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.http import FileResponse
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


class GramUserViewSet(UserViewSet):
    queryset = User.objects.all()
    pagination_class = LimitPagination
    permission_classes = (AllowAny,)
    serializer_class = GramUserSerializer

    @action(
        methods=('put',),
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
        methods=('get',),
        detail=False,
        permission_classes=(IsAuthenticated,)
    )
    def me(self, request, *args, **kwargs):
        self.get_object = self.get_instance
        return self.retrieve(request, *args, **kwargs)

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,)
    )
    def subscribe(self, request, id):
        user = request.user
        author = get_object_or_404(User, id=id)
        serializer = FollowCreateSerializer(
            context={'request': request},
            data={
                'author': author.id,
                'user': user.id
            }
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        users_annotated = User.objects.annotate(
            recipes_count=Count('recipes'))
        author_annotated = users_annotated.filter(id=id).first()
        serializer = FollowSerializer(
            author_annotated,
            context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscribe(self, request, id):
        user = request.user
        author = get_object_or_404(User, id=id)
        delete_author, _ = (
            Follow.objects.filter(user=user, author=author).delete()
        )
        if delete_author:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'detail': 'Вы не подписаны на этого пользователя.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(IsAuthenticated,),
        url_name='subscriptions',
        url_path='subscriptions',
    )
    def get_subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(subscriber__user=user).annotate(
            recipes_count=Count('recipes')
        ).order_by('username')
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
        methods=('get',),
        permission_classes=(IsAuthenticated,),
        url_path='download_shopping_cart',
        url_name='download_shopping_cart',
    )
    def download_shopping_cart(self, request):
        ingredients = RecipeIngredient.objects.filter(
            recipe__shopping_cart__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit',
        ).order_by(
            'ingredient__name'
        ).annotate(
            total=Sum('amount')
        )
        shopping_list = self.shopping_cart_in_file(ingredients)
        response = FileResponse(shopping_list, content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response

    @action(
        detail=True,
        methods=('get',),
        permission_classes=(AllowAny,),
        url_path='get-link',
        url_name='get-link',
    )
    def get_link(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        short_link = reverse(short_url, args=[recipe.pk])
        return Response({'short-link': request.build_absolute_uri(short_link)},
                        status=status.HTTP_200_OK)

    def create_obj(self, user, obj_ser, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        serializer = obj_ser(
            data={
                'recipe': recipe,
                'user': user
            }
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(recipe=recipe, user=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,),
        url_path='favorite',
        url_name='favorite',
    )
    def favorite(self, request, pk):
        return self.create_obj(request.user, FavoriteSerializer, pk)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk):
        return self.delete_obj(self, Favorite, pk)

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(IsAuthenticated,),
        url_path='shopping_cart',
        url_name='shopping_cart',
    )
    def shopping_cart(self, request, pk):
        return self.create_obj(request.user, ShoppingCartSerializer, pk)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk):
        return self.delete_obj(self, ShoppingCart, pk)

    @staticmethod
    def delete_obj(self, model, pk):
        user = self.request.user
        recipe = get_object_or_404(Recipe, pk=pk)
        deleted_object, _ = (
            model.objects.filter(recipe=recipe, user=user).delete()
        )
        if deleted_object:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'detail': 'Рецепта нет в списке.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @staticmethod
    def shopping_cart_in_file(ingredients):
        shopping_list = ['Список покупок\n']
        shopping_list += [
            f'{ingredient["ingredient__name"]} - '
            f'{ingredient["total"]} '
            f'({ingredient["ingredient__measurement_unit"]})\n'
            for ingredient in ingredients
        ]
        return shopping_list


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (OwnerOrReadOnly,)


@require_GET
def short_url(request, pk):
    if not Recipe.objects.filter(pk=pk).exists():
        raise status.Http404(f'Рецепт с  id "{pk}"  не существует.')
    return redirect(f'/recipes/{pk}/')
