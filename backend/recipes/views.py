from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_GET
from rest_framework.reverse import reverse

from recipes.models import Recipe


@require_GET
def short_url(request, pk):
    get_object_or_404(Recipe, pk=pk)
    return redirect(reverse('recipes', args=[pk]))
