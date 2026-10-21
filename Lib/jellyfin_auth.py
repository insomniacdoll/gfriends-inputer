# -*- coding:utf-8 -*-
# Emby / Jellyfin 认证兼容辅助函数
# Jellyfin 12.0 起默认禁用旧版认证（小写 api_key 查询参数、X-Emby-* 头），
# 需要使用标准的 Authorization: MediaBrowser 头。


def requires_modern_auth(product_name, version):
    """判断服务器是否为需要新版认证的 Jellyfin 12+。"""
    if not product_name or 'jellyfin' not in str(product_name).lower():
        return False
    try:
        major = int(str(version).split('.')[0])
    except (TypeError, ValueError, IndexError):
        return False
    return major >= 12


def authorization_headers(api_key):
    """生成 Jellyfin 10.8+ / 12+ 支持的标准认证头。"""
    return {'Authorization': 'MediaBrowser Token="%s"' % api_key}


def request_headers(api_key, modern_auth, extra=None):
    """仅为媒体服务器请求组合认证头，避免把密钥发送给第三方站点。"""
    headers = dict(extra or {})
    if modern_auth:
        headers.update(authorization_headers(api_key))
    return headers


def api_url(host_url, path, api_key, modern_auth):
    """按认证方式拼接 API 地址：新版认证不再把密钥放进查询参数。"""
    if modern_auth:
        return host_url + path
    return host_url + path + '?api_key=' + api_key
