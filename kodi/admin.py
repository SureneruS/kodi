from typing import Any

try:
    from sqladmin import BaseView, ModelView, expose
    from starlette.requests import Request
    from starlette.responses import Response
except ImportError as e:
    raise ImportError("sqladmin package required. Install with: pip install kodi[admin]") from e

from kodi.core import invalidate_cache
from kodi.models import Flag, TenantFlag, UserFlag


class FlagAdmin(ModelView, model=Flag):
    name = "Feature Flag"
    name_plural = "Feature Flags"
    icon = "fa-solid fa-flag"

    column_list = [Flag.name, Flag.enabled, Flag.description, Flag.updated_at]
    column_searchable_list = [Flag.name, Flag.description]
    column_sortable_list = [Flag.name, Flag.enabled, Flag.created_at, Flag.updated_at]
    column_default_sort = ("name", False)

    column_details_list = [
        Flag.name,
        Flag.description,
        Flag.enabled,
        Flag.created_at,
        Flag.updated_at,
        Flag.tenant_overrides,
        Flag.user_overrides,
    ]

    form_columns = [Flag.name, Flag.description, Flag.enabled]

    async def after_model_change(
        self, data: dict[str, Any], model: Flag, is_created: bool, request: Request
    ) -> None:
        await invalidate_cache("flags")

    async def after_model_delete(self, model: Flag, request: Request) -> None:
        await invalidate_cache("flags")


class TenantFlagAdmin(ModelView, model=TenantFlag):
    name = "Tenant Override"
    name_plural = "Tenant Overrides"
    icon = "fa-solid fa-building"

    column_list = [
        TenantFlag.flag, TenantFlag.tenant_id, TenantFlag.enabled, TenantFlag.updated_at
    ]
    column_searchable_list = [TenantFlag.tenant_id]
    column_sortable_list = [TenantFlag.tenant_id, TenantFlag.enabled, TenantFlag.updated_at]
    column_default_sort = ("tenant_id", False)

    form_columns = [TenantFlag.flag, TenantFlag.tenant_id, TenantFlag.enabled]

    async def after_model_change(
        self, data: dict[str, Any], model: TenantFlag, is_created: bool, request: Request
    ) -> None:
        await invalidate_cache("tenant", tenant_id=model.tenant_id)

    async def after_model_delete(self, model: TenantFlag, request: Request) -> None:
        await invalidate_cache("tenant", tenant_id=model.tenant_id)


class UserFlagAdmin(ModelView, model=UserFlag):
    name = "User Override"
    name_plural = "User Overrides"
    icon = "fa-solid fa-user"

    column_list = [
        UserFlag.flag, UserFlag.tenant_id, UserFlag.user_id, UserFlag.enabled, UserFlag.updated_at
    ]
    column_searchable_list = [UserFlag.tenant_id, UserFlag.user_id]
    column_sortable_list = [
        UserFlag.tenant_id, UserFlag.user_id, UserFlag.enabled, UserFlag.updated_at
    ]
    column_default_sort = [("tenant_id", False), ("user_id", False)]

    form_columns = [UserFlag.flag, UserFlag.tenant_id, UserFlag.user_id, UserFlag.enabled]

    async def after_model_change(
        self, data: dict[str, Any], model: UserFlag, is_created: bool, request: Request
    ) -> None:
        await invalidate_cache("user", tenant_id=model.tenant_id, user_id=model.user_id)

    async def after_model_delete(self, model: UserFlag, request: Request) -> None:
        await invalidate_cache("user", tenant_id=model.tenant_id, user_id=model.user_id)


class FlagDashboard(BaseView):
    name = "Flag Dashboard"
    icon = "fa-solid fa-gauge"

    @expose("/flag-dashboard", methods=["GET"])
    async def flag_dashboard(self, request: Request) -> Response:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        session = request.state.session

        flags = (
            await session.execute(
                select(Flag)
                .options(selectinload(Flag.tenant_overrides), selectinload(Flag.user_overrides))
                .order_by(Flag.name)
            )
        ).scalars().all()

        html = self._render_dashboard(flags)
        return Response(content=html, media_type="text/html")

    def _render_dashboard(self, flags: list[Flag]) -> str:
        rows = []
        for flag in flags:
            tenant_overrides = ", ".join(
                f"{o.tenant_id}: {'✓' if o.enabled else '✗'}"
                for o in flag.tenant_overrides
            ) or "—"

            user_overrides = ", ".join(
                f"{o.tenant_id}/{o.user_id}: {'✓' if o.enabled else '✗'}"
                for o in flag.user_overrides
            ) or "—"

            status = "✓ Enabled" if flag.enabled else "✗ Disabled"
            status_class = "text-success" if flag.enabled else "text-danger"

            rows.append(f"""
                <tr>
                    <td><strong>{flag.name}</strong></td>
                    <td class="{status_class}">{status}</td>
                    <td><small>{flag.description or '—'}</small></td>
                    <td><small>{tenant_overrides}</small></td>
                    <td><small>{user_overrides}</small></td>
                </tr>
            """)

        bootstrap_css = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Feature Flags Dashboard</title>
            <link href="{bootstrap_css}" rel="stylesheet">
            <style>
                body {{ padding: 20px; }}
                .text-success {{ color: #198754; }}
                .text-danger {{ color: #dc3545; }}
            </style>
        </head>
        <body>
            <div class="container-fluid">
                <h2 class="mb-4">Feature Flags Dashboard</h2>
                <table class="table table-striped table-hover">
                    <thead class="table-dark">
                        <tr>
                            <th>Flag Name</th>
                            <th>Global Status</th>
                            <th>Description</th>
                            <th>Tenant Overrides</th>
                            <th>User Overrides</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(rows)}
                    </tbody>
                </table>
                <p class="text-muted">
                    <small>✓ = Enabled, ✗ = Disabled</small>
                </p>
            </div>
        </body>
        </html>
        """
