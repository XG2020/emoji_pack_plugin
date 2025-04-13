import httpx
import urllib.parse
from typing import List
from pydantic import BaseModel, Field

from nekro_agent.services.plugin.base import NekroPlugin, ConfigBase, SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core import logger

# 插件实例
plugin = NekroPlugin(
    name="表情包搜索插件",
    module_name="emoji_pack_plugin",
    description="根据关键词搜索表情包图片",
    version="1.0.0",
    author="XGGM",
    url="https://github.com/XG2020/emoji_pack_plugin",
)

@plugin.mount_config()
class EmojiSearchConfig(ConfigBase):
    """表情包搜索配置"""
    API_URL: str = Field(
        default="https://cn.apihz.cn/api/img/apihzbqbbaidu.php",
        title="API地址",
        description="表情包搜索API的基础URL，<a href='https://www.apihz.cn/api/apihzbqbbaidu.html' target='_blank'>接口文档</a>",
    )
    TIMEOUT: int = Field(
        default=10,
        title="请求超时时间",
        description="API请求的超时时间(秒)",
    )
    USER_ID: str = Field(
        default="88888888",
        title="用户ID",
        description="访问API所需的用户ID",
        env="EMOJI_SEARCH_USER_ID"
    )
    USER_KEY: str = Field(
        default="88888888",
        title="用户秘钥",
        description="访问API所需的用户秘钥",
        env="EMOJI_SEARCH_USER_KEY"
    )
    EXTRA_KEYWORD: str = Field(
        default="",
        title="附加关键词",
        description="搜索时会自动附加的关键词，如'二次元'",
    )

# 获取配置
config = plugin.get_config(EmojiSearchConfig)

class SearchResult(BaseModel):
    """表情包搜索结果模型"""
    image_urls: List[str]
    current_page: int
    max_page: int
    total_count: int

async def _search_emoji(
    keywords: str,
    page: int = 1,
    limit: int = 1
) -> SearchResult:
    """执行表情包搜索
    
    Args:
        keywords: 搜索关键词
        page: 页码(默认为1)
        limit: 每页结果数量(默认为1)
    
    Returns:
        SearchResult: 搜索结果对象
        
    Raises:
        httpx.RequestError: 网络请求错误
        httpx.HTTPStatusError: HTTP状态错误
        ValueError: 数据解析错误
    """
    # 如果配置中有附加关键词，合并到搜索词中
    search_words = keywords
    if config.EXTRA_KEYWORD:
        search_words = f"{keywords} {config.EXTRA_KEYWORD}"
    
    params = {
        "id": config.USER_ID,
        "key": config.USER_KEY,
        "words": urllib.parse.quote(search_words),
        "page": page,
        "limit": limit
    }
    
    async with httpx.AsyncClient(timeout=config.TIMEOUT) as client:
        response = await client.get(config.API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("code") != 200:
            raise ValueError(f"API返回错误: {data.get('msg', '未知错误')}")
        
        return SearchResult(
            image_urls=data.get("res", []),
            current_page=int(data.get("page", 1)),
            max_page=int(data.get("maxpage", 1)),
            total_count=int(data.get("count", 0))
        )

@plugin.mount_sandbox_method(
    SandboxMethodType.MULTIMODAL_AGENT,
    name="搜索表情包",
    description="根据关键词搜索表情包图片并返回",
)
async def search_emoji(
    _ctx: AgentCtx, 
    keywords: str, 
    page: int = 1,
    limit: int = 1
) -> str:
    """根据关键词搜索表情包图片
    
    Args:
        keywords: 搜索关键词，如"开心"、"难过"
        page: 页码(默认为1)
        limit: 每页结果数量(默认为1)
    
    Returns:
        str: 搜索结果描述，包含图片URL
        
    Example:
        search_emoji("开心", limit=3)
    """
    try:
        # 验证参数
        if not keywords:
            return "请提供搜索关键词"
        
        if len(keywords) > 100:
            return "关键词长度不能超过100个字符"
        
        limit = min(100, max(1, limit))
        
        # 执行搜索
        result = await _search_emoji(keywords, page, limit)
        
        if not result.image_urls:
            return f"没有找到与'{keywords}'相关的表情包"
        
        # 构造返回结果
        response = [
            f"找到{result.total_count}个表情包(第{result.current_page}页，共{result.max_page}页):"
        ]
        
        for idx, url in enumerate(result.image_urls, 1):
            if limit > 1:
                response.append(f"{idx}. {url}")
            else:
                response.append(url)
                
        return "\n".join(response)
    
    except httpx.RequestError as e:
        logger.error(f"表情包搜索请求失败: {e}")
        return f"表情包搜索失败，无法连接到服务: {str(e)}"
    except httpx.HTTPStatusError as e:
        logger.error(f"表情包搜索HTTP错误: {e}")
        return f"表情包搜索失败，服务返回错误: {e.response.status_code}"
    except ValueError as e:
        logger.error(f"表情包数据解析错误: {e}")
        return f"表情包搜索失败: {str(e)}"
    except Exception as e:
        logger.error(f"表情包搜索未知错误: {e}")
        return f"表情包搜索发生未知错误: {str(e)}"

@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件资源"""
    # 当前无需清理资源
    logger.info("表情包搜索插件资源已清理")
