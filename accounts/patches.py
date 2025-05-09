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
        
        # Import trực tiếp các hàm phụ trợ
        from social_core.utils import setting_url, user_is_authenticated, user_is_active
        
        # Tạo hàm thay thế cho partial_pipeline_data nếu không import được
        def simple_partial_pipeline_data(backend, user=None, *args, **kwargs):
            # Implement giản lược nếu không thể import được
            try:
                from social_core.pipeline.partial import partial_pipeline_data as original_partial
                return original_partial(backend, user, *args, **kwargs)
            except ImportError:
                logger.warning("Không thể import partial_pipeline_data, sử dụng hàm giản lược")
                # Trả về None thay vì raise lỗi
                return None

        # Định nghĩa hàm thay thế
        def patched_do_complete(backend, login, user=None, redirect_name="next", *args, **kwargs):
            """
            Phiên bản đã sửa của hàm do_complete để xử lý trường hợp social_user là None
            """
            data = backend.strategy.request_data()
            is_authenticated = user_is_authenticated(user)
            user = user if is_authenticated else None

            # Sử dụng hàm wrapper thay vì import trực tiếp
            partial = simple_partial_pipeline_data(backend, user, *args, **kwargs)
            if partial:
                try:
                    user = backend.continue_pipeline(partial)
                    # clean partial data after usage
                    backend.strategy.clean_partial_pipeline(partial.token)
                except Exception as e:
                    logger.warning(f"Lỗi khi tiếp tục pipeline: {str(e)}")
            else:
                try:
                    user = backend.complete(user=user, redirect_name=redirect_name, *args, **kwargs)
                except Exception as e:
                    logger.warning(f"Lỗi khi hoàn thành backend: {str(e)}")
                    # Nếu xảy ra lỗi, chuyển hướng về trang lỗi
                    return backend.strategy.redirect(setting_url(backend, "", "LOGIN_ERROR_URL", "LOGIN_URL"))

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
                    try:
                        login(backend, user, social_user)
                    except Exception as e:
                        logger.warning(f"Lỗi khi đăng nhập: {str(e)}")
                    
                    # Lưu thông tin đăng nhập vào session (chỉ khi social_user không phải None)
                    if social_user is not None:
                        try:
                            backend.strategy.session_set(
                                "social_auth_last_login_backend", social_user.provider
                            )
                        except AttributeError:
                            logger.warning("social_user không có thuộc tính provider, sử dụng backend.name")
                            # Nếu vẫn gặp lỗi, lưu thông tin backend
                            backend.strategy.session_set(
                                "social_auth_last_login_backend", backend.name
                            )
                    else:
                        # Lưu tên backend nếu social_user là None
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
                        try:
                            login(backend, user, social_user)
                        except Exception as e:
                            logger.warning(f"Lỗi khi đăng nhập người dùng không hoạt động: {str(e)}")
                    url = setting_url(
                        backend, "INACTIVE_USER_URL", "LOGIN_ERROR_URL", "LOGIN_URL"
                    )
            else:
                url = setting_url(backend, "LOGIN_ERROR_URL", "LOGIN_URL")

            # Đảm bảo luôn có một URL chuyển hướng
            if not url:
                logger.warning("URL không được thiết lập, sử dụng LOGIN_URL")
                url = backend.setting("LOGIN_URL", "/")

            try:
                if redirect_value and redirect_value != url:
                    from urllib.parse import quote
                    redirect_value = quote(redirect_value)
                    url += ("&" if "?" in url else "?") + f"{redirect_name}={redirect_value}"

                if backend.setting("SANITIZE_REDIRECTS", True):
                    try:
                        from social_core.utils import sanitize_redirect
                        allowed_hosts = [
                            *backend.setting("ALLOWED_REDIRECT_HOSTS", []),
                            backend.strategy.request_host(),
                        ]
                        sanitized = sanitize_redirect(allowed_hosts, url)
                        if sanitized:
                            url = sanitized
                        else:
                            url = backend.setting("LOGIN_REDIRECT_URL", "/")
                    except Exception as e:
                        logger.warning(f"Lỗi khi sanitize URL: {str(e)}")
                
                return backend.strategy.redirect(url)
            except Exception as e:
                logger.error(f"Lỗi khi redirect: {str(e)}")
                # Nếu có lỗi, trả về redirect đơn giản
                return backend.strategy.redirect(backend.setting("LOGIN_URL", "/"))

        # Áp dụng patch
        actions.do_complete = patched_do_complete
        logger.info("Successfully patched social_core.actions.do_complete")
        
    except Exception as e:
        logger.error(f"Error patching social_core.actions: {str(e)}", exc_info=True) 