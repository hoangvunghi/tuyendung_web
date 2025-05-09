"""
Patches để khắc phục lỗi và sửa đổi hành vi của các thư viện ngoài
"""

import logging
import importlib
from django.conf import settings
from django.shortcuts import redirect

logger = logging.getLogger(__name__)

def apply_patches():
    """
    Áp dụng tất cả patches cho thư viện social_core và các thư viện khác
    """
    patch_social_core_actions()

def patch_social_core_actions():
    """
    Ghi đè hàm do_complete trong social_core.actions để xử lý lỗi
    'NoneType' object has no attribute 'provider'
    """
    try:
        # Import module cần patch
        from social_core import actions
        original_do_complete = actions.do_complete

        # Định nghĩa hàm thay thế
        def patched_do_complete(backend, login, user=None, redirect_name="next", *args, **kwargs):
            """
            Phiên bản đã sửa của hàm do_complete để xử lý trường hợp social_user là None
            """
            data = backend.strategy.request_data()
            is_authenticated = user_is_authenticated(user)
            user = user if is_authenticated else None

            partial = partial_pipeline_data(backend, user, *args, **kwargs)
            if partial:
                user = backend.continue_pipeline(partial)
                # clean partial data after usage
                backend.strategy.clean_partial_pipeline(partial.token)
            else:
                user = backend.complete(user=user, redirect_name=redirect_name, *args, **kwargs)

            # Lấy URL redirect
            redirect_value = backend.strategy.session_get(redirect_name, "") or data.get(
                redirect_name, ""
            )

            # Kiểm tra kết quả
            user_model = backend.strategy.storage.user.user_model()
            if user and not isinstance(user, user_model):
                return user

            if is_authenticated:
                if not user:
                    url = setting_url(backend, redirect_value, "LOGIN_REDIRECT_URL")
                else:
                    url = setting_url(
                        backend,
                        redirect_value,
                        "NEW_ASSOCIATION_REDIRECT_URL",
                        "LOGIN_REDIRECT_URL",
                    )
            elif user:
                if user_is_active(user):
                    # catch is_new/social_user in case login() resets the instance
                    is_new = getattr(user, "is_new", False)
                    social_user = getattr(user, 'social_user', None)
                    
                    # Đăng nhập người dùng
                    login(backend, user, social_user)
                    
                    # Lưu thông tin đăng nhập vào session (chỉ khi social_user không phải None)
                    if social_user is not None:
                        try:
                            backend.strategy.session_set(
                                "social_auth_last_login_backend", social_user.provider
                            )
                        except AttributeError:
                            logger.warning("social_user không có thuộc tính provider, bỏ qua")
                            # Nếu vẫn gặp lỗi, lưu thông tin backend
                            backend.strategy.session_set(
                                "social_auth_last_login_backend", backend.name
                            )

                    # Xác định URL chuyển hướng
                    if is_new:
                        url = setting_url(
                            backend,
                            "NEW_USER_REDIRECT_URL",
                            redirect_value,
                            "LOGIN_REDIRECT_URL",
                        )
                    else:
                        url = setting_url(backend, redirect_value, "LOGIN_REDIRECT_URL")
                else:
                    if backend.setting("INACTIVE_USER_LOGIN", False):
                        social_user = getattr(user, 'social_user', None)
                        login(backend, user, social_user)
                    url = setting_url(
                        backend, "INACTIVE_USER_URL", "LOGIN_ERROR_URL", "LOGIN_URL"
                    )
            else:
                url = setting_url(backend, "LOGIN_ERROR_URL", "LOGIN_URL")

            assert url, "By this point URL has to have been set"

            if redirect_value and redirect_value != url:
                from urllib.parse import quote
                redirect_value = quote(redirect_value)
                url += ("&" if "?" in url else "?") + f"{redirect_name}={redirect_value}"

            if backend.setting("SANITIZE_REDIRECTS", True):
                from social_core.utils import sanitize_redirect
                allowed_hosts = [
                    *backend.setting("ALLOWED_REDIRECT_HOSTS", []),
                    backend.strategy.request_host(),
                ]
                url = sanitize_redirect(allowed_hosts, url) or backend.setting(
                    "LOGIN_REDIRECT_URL"
                )
            return backend.strategy.redirect(url)

        # Import các hàm phụ trợ cần thiết
        from social_core.utils import setting_url, user_is_authenticated, user_is_active
        from social_core.pipeline.partial import partial_pipeline_data

        # Áp dụng patch
        actions.do_complete = patched_do_complete
        logger.info("Successfully patched social_core.actions.do_complete")
        
    except Exception as e:
        logger.error(f"Error patching social_core.actions: {str(e)}", exc_info=True) 