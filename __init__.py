import httpx
from typing import Dict, List
from pydantic import BaseModel, Field
from urllib.parse import quote

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
    USER_ID: str = Field(
        default="88888888",
        title="用户ID",
        description="用户中心的数字ID，必需配置",
    )
    USER_KEY: str = Field(
        default="",
        title="88888888",
        description="用户中心通讯秘钥，必需配置",
    )
    TIMEOUT: int = Field(
        default=15,
        title="请求超时时间",
        description="API请求的超时时间(秒)",
    )
    EXTRA_KEYWORD: str = Field(
        default="",
        title="额外关键词",
        description="在搜索时会自动附加的关键词，可为空",
    )

# 获取配置
config = plugin.get_config(EmojiSearchConfig)
if not config.USER_ID or not config.USER_KEY:
    logger.error("表情包搜索插件配置错误: 必须配置USER_ID和USER_KEY")

@plugin.mount_sandbox_method(
    SandboxMethodType.MULTIMODAL_AGENT,
    name="搜索表情包",
    description="根据关键词搜索表情包图片，返回一个合适的表情包图片地址",
)
async def search_emoji(_ctx: AgentCtx, keyword: str) -> str:
    """根据关键词搜索表情包图片
    
    会根据配置中的额外关键词自动附加到搜索词中，随机返回一个搜索结果中的图片URL。

    Args:
        keyword: 表情包关键词，如"开心"、"生气"等

    Returns:
        str: 表情包图片URL
        
    Raises:
        ValueError: 当keyword参数为空或过长时抛出
        
    Example:
        search_emoji("开心")
    """
    if not keyword:
        raise ValueError("关键词不能为空")
    if len(keyword) > 100:
        raise ValueError("关键词长度不能超过100个汉字")
    
    try:
        # 处理搜索关键词
        search_words = keyword.strip()
        if config.EXTRA_KEYWORD:
            search_words = f"{search_words} {config.EXTRA_KEYWORD}"
        
        # 准备POST请求参数
        params = {
            "id": config.USER_ID,
            "key": config.USER_KEY,
            "words": search_words,
            "page": 1,
            "limit": 10,  # 获取10个结果随机选择
        }
        
        async with httpx.AsyncClient(timeout=config.TIMEOUT) as client:
            # 使用POST方式请求
            response = await client.post(
                config.API_URL,
                data=params
            )
            
            data = response.json()
            
            if data["code"] != 200:
                logger.error(f"表情包搜索失败: {data.get('msg', '未知错误')}")
                return f"表情包搜索失败: {data.get('msg', '未知错误')}"
                
            if not data.get("res"):
                return "未找到匹配的表情包"
            
            # 从结果中随机选择一个表情包(这里取第一个以确保可预测性)
            return data["res"][0]
            
    except httpx.RequestError as e:
        logger.error(f"表情包搜索请求失败: {e}")
        return f"表情包搜索失败，无法连接到服务: {str(e)}"
    except httpx.HTTPStatusError as e:
        logger.error(f"表情包搜索HTTP错误: {e}")
        return f"表情包搜索失败，服务返回错误: {e.response.status_code}"
    except ValueError as e:
        logger.error(f"表情包搜索参数错误: {e}")
        return f"表情包搜索参数错误: {str(e)}"
    except Exception as e:
        logger.error(f"表情包搜索未知错误: {e}")
        return f"表情包搜索发生未知错误: {str(e)}"

@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件资源"""
    # 当前无需清理资源
    logger.info("表情包搜索插件资源已清理")
