try:
    from sqladmin import ModelView
except ImportError:
    raise ImportError("sqladmin package required. Install with: pip install kodi[admin]")

from kodi.core import invalidate_cache
from kodi.models import Flag, TenantFlag, UserFlag


class FlagAdmin(ModelView, model=Flag):
    name = "Feature Flags"
    name_plural = "Feature Flags"
    icon = "fa-solid fa-flag"

    column_list = [Flag.name, Flag.enabled, Flag.description, Flag.updated_at]
    column_searchable_list = [Flag.name, Flag.description]
    column_sortable_list = [Flag.name, Flag.enabled, Flag.created_at, Flag.updated_at]
    column_default_sort = ("name", False)

    form_columns = [Flag.name, Flag.description, Flag.enabled]

    async def after_model_change(self, data: dict, model: Flag, is_created: bool, request) -> None:  # type: ignore
        await invalidate_cache("flags")

    async def after_model_delete(self, model: Flag, request) -> None:  # type: ignore
        await invalidate_cache("flags")


class TenantFlagAdmin(ModelView, model=TenantFlag):
    name = "Tenant Flag Override"
    name_plural = "Tenant Flag Overrides"
    icon = "fa-solid fa-building"

    column_list = [TenantFlag.tenant_id, TenantFlag.flag, TenantFlag.enabled, TenantFlag.updated_at]
    column_searchable_list = [TenantFlag.tenant_id]
    column_sortable_list = [TenantFlag.tenant_id, TenantFlag.enabled, TenantFlag.updated_at]
    column_default_sort = ("tenant_id", False)

    form_columns = [TenantFlag.flag, TenantFlag.tenant_id, TenantFlag.enabled]

    async def after_model_change(  # type: ignore
        self, data: dict, model: TenantFlag, is_created: bool, request
    ) -> None:
        await invalidate_cache("tenant", tenant_id=model.tenant_id)

    async def after_model_delete(self, model: TenantFlag, request) -> None:  # type: ignore
        await invalidate_cache("tenant", tenant_id=model.tenant_id)


class UserFlagAdmin(ModelView, model=UserFlag):
    name = "User Flag Override"
    name_plural = "User Flag Overrides"
    icon = "fa-solid fa-user"

    column_list = [
        UserFlag.tenant_id, UserFlag.user_id, UserFlag.flag, UserFlag.enabled, UserFlag.updated_at
    ]
    column_searchable_list = [UserFlag.tenant_id, UserFlag.user_id]
    column_sortable_list = [
        UserFlag.tenant_id, UserFlag.user_id, UserFlag.enabled, UserFlag.updated_at
    ]
    column_default_sort = [("tenant_id", False), ("user_id", False)]

    form_columns = [UserFlag.flag, UserFlag.tenant_id, UserFlag.user_id, UserFlag.enabled]

    async def after_model_change(  # type: ignore
        self, data: dict, model: UserFlag, is_created: bool, request
    ) -> None:
        await invalidate_cache("user", tenant_id=model.tenant_id, user_id=model.user_id)

    async def after_model_delete(self, model: UserFlag, request) -> None:  # type: ignore
        await invalidate_cache("user", tenant_id=model.tenant_id, user_id=model.user_id)
