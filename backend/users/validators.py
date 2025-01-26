import re

from django.core.exceptions import ValidationError


def validate_username(username):
    invalid_chars = re.sub(r'[\w.@+-]+', '', username)
    if invalid_chars:
        raise ValidationError(
            'Данные символы недопустимы: {}'.format(
                ''.join(set(invalid_chars))
            )
        )
    return username
