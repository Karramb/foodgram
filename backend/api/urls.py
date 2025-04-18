from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import (GramUserViewSet, IngredientViewSet, RecipeViewSet,
                       TagViewSet)

app_name = 'api'

router_v1 = DefaultRouter()
router_v1.register(r'ingredients', IngredientViewSet, basename='ingredients')
router_v1.register(r'recipes', RecipeViewSet, basename='recipes')
router_v1.register(r'tags', TagViewSet, basename='tags')
router_v1.register(r'users', GramUserViewSet, basename='users')

urls = [
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router_v1.urls))
]
