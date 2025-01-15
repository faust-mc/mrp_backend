import re
from django.core.exceptions import ValidationError

class UppercasePasswordValidator:
    def validate(self, password, user=None):
        if not re.search(r'[A-Z]', password):
            raise ValidationError("Password must contain at least one uppercase letter.")

    def get_help_text(self):
        return "Your password must contain at least one uppercase letter."

class LowercasePasswordValidator:
    def validate(self, password, user=None):
        if not re.search(r'[a-z]', password):
            raise ValidationError("Password must contain at least one lowercase letter.")

    def get_help_text(self):
        return "Your password must contain at least one lowercase letter."


class SpecialCharacterPasswordValidator:
    def validate(self, password, user=None):
        if not re.search(r'[\W_]', password):
            raise ValidationError("Password must contain at least one special character.")

    def get_help_text(self):
        return "Your password must contain at least one special character."



class NumericPasswordValidator:
    def validate(self, password, user=None):
        if not re.search(r'\d', password):
            raise ValidationError("Password must contain at least one number.")

    def get_help_text(self):
        return "Your password must contain at least one number."
