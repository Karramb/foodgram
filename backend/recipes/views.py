from django.shortcuts import redirect
from django.views.decorators.http import require_GET
from rest_framework import status

from recipes.models import Recipe


@require_GET
def short_url(request, pk):
    if not Recipe.objects.filter(pk=pk).exists():
        raise status.Http404(f'Рецепт с  id "{pk}"  не существует.')
    return redirect(f"/recipes/{pk}/")
