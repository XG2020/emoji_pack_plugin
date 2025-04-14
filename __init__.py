import httpx
import random
from typing import Dict, List
from pydantic import BaseModel, Field, HttpUrl
from urllib.parse import quote

from nekro_agent.services.plugin.base import NekroPlugin, ConfigBase, SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core import logger

# 插件实例
plugin = NekroPlugin(
    name="表情包搜索插件",
    module_name="emo_plugin",
    description="根据关键词搜索表情包图片",
    version="1.0.0",
    author="XGGM",
    url="https://github.com/XG2020/emo_plugin",
)

@plugin.mount_config()
class EmojiSearchConfig(ConfigBase):
    """表情包搜索配置"""
    API_URL: str = Field(
        default="https://cn.apihz.cn/api/img/apihzbqbbaidu.php",
        title="表情包API地址",
        description="表情包搜索API, <a href='https://www.apihz.cn/api/apihzbqbbaidu.html' target='_blank'>接口文档</a>",
    )
    USER_ID: str = Field(
        default="88888888",
        title="用户ID",
        description="API访问所需的用户数字ID，默认为公共ID，共享每分钟调用频次",
    )
    USER_KEY: str = Field(
        default="88888888",
        title="用户KEY",
        description="API访问所需的通讯秘钥，默认为公共KEY，共享每分钟调用频次",
    )
    EXTRA_KEYWORD: str = Field(
        default="",
        title="额外关键词",
        description="搜索时会自动添加的关键词，如'二次元'",
    )
    TIMEOUT: int = Field(
        default=10,
        title="请求超时时间",
        description="API请求的超时时间(秒)",
    )

# 获取配置
config = plugin.get_config(EmojiSearchConfig)

async def fetch_emoji_images(keyword: str, limit: int = 1, page: int = 1) -> Dict:
    """从API获取表情包图片数据
    
    Args:
        keyword: 搜索关键词
        limit: 返回结果数量
        page: 页码
        
    Returns:
        Dict: API返回的JSON数据
        
    Raises:
        httpx.RequestError: 网络请求错误
        httpx.HTTPStatusError: HTTP状态码错误
        ValueError: 数据解析错误
    """
    full_keyword = f"{keyword} {config.EXTRA_KEYWORD}".strip()
    encoded_keyword = quote(full_keyword)
    
    params = {
        "id": config.USER_ID,
        "key": config.USER_KEY,
        "words": encoded_keyword,
        "limit": limit,
        "page": page
    }
    
    async with httpx.AsyncClient(timeout=config.TIMEOUT) as client:
        response = await client.post(config.API_URL, params=params)
        response.raise_for_status()
        return response.json()

def format_result(data: Dict) -> str:
    """格式化API返回结果
    
    Args:
        data: API返回的JSON数据
        
    Returns:
        str: 格式化后的结果字符串
        
    Raises:
        KeyError: 缺少必要字段
        ValueError: 数据格式错误
    """
    if data["code"] != 200:
        raise ValueError(f"API返回错误: {data.get('msg', '未知错误')}")
    
    res_list: List[str] = data["res"]
    if not res_list:
        raise ValueError("没有找到匹配的表情包")
    
    count = data["count"]
    maxpage = data["maxpage"]
    
    return (
        f"找到{count}个表情包，当前第{data['page']}/{maxpage}页\n"
        f"随机选择一个: {random.choice(res_list)}"
    )

@plugin.mount_sandbox_method(
    SandboxMethodType.MULTIMODAL_AGENT,
    name="搜索表情包",
    description="根据关键词搜索表情包图片，并返回图片内容",
)
async def search_emoji(_ctx: AgentCtx, keyword: str) -> str:
    """根据关键词搜索表情包图片
    
    Args:
        keyword: 表情包搜索关键词，如"开心"、"伤心"
        
    Returns:
        str: 搜索结果的文本描述和图片URL
        
    Example:
        search_emoji("开心")
    """
    try:
        # 获取表情包数据
        data = await fetch_emoji_images(keyword)
        return format_result(data)
    except httpx.RequestError as e:
        logger.error(f"表情包搜索请求失败: {e}")
        return f"表情包搜索失败，无法连接到服务: {str(e)}"
    except httpx.HTTPStatusError as e:
        logger.error(f"表情包搜索HTTP错误: {e}")
        return f"表情包搜索失败，服务返回错误: {e.response.status_code}"
    except (KeyError, ValueError) as e:
        logger.error(f"表情包数据解析错误: {e}")
        return f"表情包数据解析失败: {str(e)}"
    except Exception as e:
        logger.error(f"表情包搜索未知错误: {e}")
        return f"表情包搜索发生未知错误: {str(e)}"

@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="获取表情包图片",
    description="获取指定URL的表情包图片内容",
)
async def get_emoji_image(_ctx: AgentCtx, image_url: str) -> bytes:
    """从URL获取表情包图片内容
    
    Args:
        image_url: 图片的完整URL
        
    Returns:
        bytes: 图片的二进制数据
        
    Example:
        get_emoji_image("https://example.com/image.jpg")
    """
    try:
        async with httpx.AsyncClient(timeout=config.TIMEOUT) as client:
            response = await client.get(image_url)
            response.raise_for_status()
            return response.content
    except httpx.RequestError as e:
        logger.error(f"图片下载失败: {e}")
        raise ValueError(f"无法下载图片: {str(e)}")
    except httpx.HTTPStatusError as e:
        logger.error(f"图片下载HTTP错误: {e}")
        raise ValueError(f"图片下载失败，HTTP状态码: {e.response.status_code}")
    except Exception as e:
        logger.error(f"图片下载未知错误: {e}")
        raise ValueError(f"图片下载发生未知错误: {str(e)}")

@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件资源"""
    # 如有必要，在此实现清理资源的逻辑
    logger.info("表情包搜索插件资源已清理")
