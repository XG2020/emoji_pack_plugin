import httpx
from typing import Dict, Any, List
from pydantic import BaseModel, Field, HttpUrl
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
class EmojiConfig(ConfigBase):
    """表情包搜索配置"""
    API_URL: HttpUrl = Field(
        default="https://cn.apihz.cn/api/img/apihzbqbbaidu.php",
        title="表情包API地址",
        description="表情包搜索API的基础URL，<a href='https://www.apihz.cn/api/apihzbqbbaidu.html' target='_blank'>接口文档</a>",
    )
    TIMEOUT: int = Field(
        default=10,
        title="请求超时时间",
        description="API请求的超时时间(秒)",
    )
    DEFAULT_LIMIT: int = Field(
        default=1,
        title="默认返回结果数量",
        description="默认情况下返回的表情包数量",
    )
    USER_ID: str = Field(
        default="88888888",
        title="用户ID",
        description="用户中心的数字ID",
    )
    USER_KEY: str = Field(
        default="88888888",
        title="用户KEY",
        description="用户中心通讯秘钥",
    )
    EXTRA_KEYWORD: str = Field(
        default="",
        title="额外关键词",
        description="在搜索表情包时添加的一个额外关键词，二次元",
    )

# 获取配置
config = plugin.get_config(EmojiConfig)

class EmojiSearchResult(BaseModel):
    """表情包搜索结果模型"""
    code: int = Field(..., title="状态码", description="200成功，400错误")
    msg: str = Field(..., title="信息提示", description="状态码为400时的错误提示")
    page: int = Field(..., title="当前页码", description="返回当前页码")
    maxpage: int = Field(..., title="最大页码", description="搜索结果的最大页码")
    count: int = Field(..., title="结果数量", description="搜索结果总数量")
    res: List[HttpUrl] = Field(..., title="结果集", description="返回表情包图片地址结果集")

@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="搜索表情包",
    description="根据关键词搜索表情包并获取图片字节流",
)
async def search_emoji(_ctx: AgentCtx, words: str) -> dict:
    """
    根据关键词搜索表情包并获取图片字节流

    Args:
        words: 搜索的表情包关键词，例如“开心”

    Returns:
        dict: 搜索结果，包含状态码、消息、表情包图片字节流等信息

    Example:
        search_emoji("伤心")
    """
    try:
        async with httpx.AsyncClient(timeout=config.TIMEOUT) as client:
            params = {
                "id": config.USER_ID,
                "key": config.USER_KEY,
                "words": words + " " + config.EXTRA_KEYWORD,
                "page": 1,
                "limit": config.DEFAULT_LIMIT,
            }
            response = await client.get(config.API_URL, params=params)
            response.raise_for_status()
            data = response.json()
            search_result = EmojiSearchResult(**data)

            if search_result.code != 200:
                return {
                    "code": search_result.code,
                    "msg": search_result.msg,
                    "data": None
                }
            
            if not search_result.res:
                return {
                    "code": 200,
                    "msg": "无搜索结果",
                    "data": None
                }

            # 获取第一张图片的字节流
            image_response = await client.get(search_result.res[0])
            image_response.raise_for_status()
            image_bytes = image_response.content
            
            return {
                "code": 200,
                "msg": "搜索成功",
                "data": image_bytes
            }
    except httpx.RequestError as e:
        logger.error(f"表情包搜索请求失败: {e}")
        return {
            "code": 400,
            "msg": f"请求失败，无法连接到服务: {str(e)}",
            "data": None
        }
    except httpx.HTTPStatusError as e:
        logger.error(f"表情包搜索HTTP错误: {e}")
        return {
            "code": 400,
            "msg": f"请求失败，服务返回错误: {e.response.status_code}",
            "data": None
        }
    except (KeyError, ValueError) as e:
        logger.error(f"表情包数据解析错误: {e}")
        return {
            "code": 400,
            "msg": f"数据解析失败: {str(e)}",
            "data": None
        }
    except Exception as e:
        logger.error(f"表情包搜索未知错误: {e}")
        return {
            "code": 400,
            "msg": f"发生未知错误: {str(e)}",
            "data": None
        }

@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件资源"""
    logger.info("表情包搜索插件资源已清理")
