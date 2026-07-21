from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AuthSession, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    ordering = ("email",)
    list_display = (
        "email",
        "first_name",
        "last_name",
        "role",
        "is_active",
        "is_staff",
        "deleted_at",
    )
    list_filter = ("is_active", "is_staff", "role")
    search_fields = ("email", "first_name", "last_name")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "middle_name", "role")} ),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")} ),
        ("Important dates", {"fields": ("last_login", "created_at", "updated_at", "deleted_at")} ),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "middle_name", "role", "password1", "password2"),
        }),
    )
    readonly_fields = ("created_at", "updated_at", "deleted_at")


@admin.register(AuthSession)
class AuthSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "jti", "created_at", "expires_at", "revoked_at")
    list_filter = ("revoked_at",)
    search_fields = ("user__email", "jti")
    readonly_fields = ("id", "jti", "created_at")
