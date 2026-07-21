from django.contrib import admin

from .models import AccessRoleRule, BusinessElement, Role


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "created_at")
    search_fields = ("code", "name")
    readonly_fields = ("created_at",)


@admin.register(BusinessElement)
class BusinessElementAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "created_at")
    search_fields = ("code", "name", "description")
    readonly_fields = ("created_at",)



@admin.register(AccessRoleRule)
class AccessRoleRuleAdmin(admin.ModelAdmin):
    list_display = (
        "role",
        "element",
        "read_permission",
        "read_all_permission",
        "create_permission",
        "update_permission",
        "update_all_permission",
        "delete_permission",
        "delete_all_permission",
    )
    list_filter = ("role", "element")
    search_fields = ("role__code", "element__code")
    readonly_fields = ("created_at", "updated_at")
