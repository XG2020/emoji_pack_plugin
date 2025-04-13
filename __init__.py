import random
import urllib.parse
from typing import List, Dict

import httpx
from pydantic import BaseModel, Field, HttpUrl

from nekro_agent.services.plugin.base import NekroPlugin, ConfigBase, SandboxMethodType
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.core import logger

# 插件实例
plugin = NekroPlugin(
    name="表情包获取插件",
    module_name="emoji_pack_plugin",
    description="根据关键词获取相关的表情包图片",
    version="1.0.0",
    author="XGGM",
    url="https://github.com/XG2020/emoji_pack_plugin",
)


@plugin.mount_config()
class EmojiPackConfig(ConfigBase):
    """表情包插件配置"""
    API_URL: HttpUrl = Field(
        default="https://cn.apihz.cn/api/img/apihzbqbbaidu.php",
        title="API地址",
        description="表情包API的基础URL，<a href='https://www.apihz.cn/api/apihzbqbbaidu.html' target='_blank'>接口文档</a>",
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
    DEFAULT_LIMIT: int = Field(
        default=10,
        title="默认返回数量",
        description="默认返回的表情包图片数量(1-100)",
        ge=1,
        le=100
    )
    TIMEOUT: int = Field(
        default=10,
        title="请求超时时间",
        description="API请求的超时时间(秒)",
    )
    EXTRA_KEYWORD: str = Field(
        default="",
        title="额外关键词",
        description="搜索时会额外附加的关键词",
    )


# 获取配置
config = plugin.get_config(EmojiPackConfig)


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="获取表情包",
    description="根据关键词获取表情包图片URL",
)
async def get_emoji_pack(_ctx: AgentCtx, keyword: str, limit: int = 1) -> List[str]:
    """根据关键词获取表情包图片URL

    Args:
        keyword: 要搜索的表情包关键词
        limit: 要返回的表情包数量(1-100)

    Returns:
        List[str]: 表情包图片URL列表

    Raises:
        ValueError: 当输入参数不合法时抛出
        Exception: 当API请求失败时抛出

    Example:
        get_emoji_pack("开心", 3)
    """
    try:
        # 参数验证
        if not keyword:
            raise ValueError("关键词不能为空")
        if limit < 1 or limit > 100:
            raise ValueError("limit参数必须在1-100之间")

        # 构造搜索关键词
        search_keyword = keyword
        if config.EXTRA_KEYWORD:
            search_keyword = f"{keyword} {config.EXTRA_KEYWORD}"

        # 构造请求参数
        params = {
            "id": config.USER_ID,
            "key": config.USER_KEY,
            "words": urllib.parse.quote(search_keyword),
            "page": 1,
            "limit": limit if limit > config.DEFAULT_LIMIT else config.DEFAULT_LIMIT
        }

        logger.info(f"请求表情包API: {config.API_URL}, 参数: {params}")

        # 发送请求
        async with httpx.AsyncClient(timeout=config.TIMEOUT) as client:
            response = await client.get(str(config.API_URL), params=params)
            response.raise_for_status()
            data = response.json()

            if data["code"] != 200:
                raise Exception(f"API返回错误: {data.get('msg', '未知错误')}")

            # 检查是否有结果
            if not data.get("res") or not isinstance(data["res"], list):
                raise Exception("API返回的结果集无效")

            # 随机选择limit个结果
            result_list = data["res"]
            if len(result_list) > limit:
                result_list = random.sample(result_list, limit)

            logger.info(f"获取到 {len(result_list)} 个表情包")
            return result_list

    except httpx.RequestError as e:
        logger.error(f"表情包请求失败: {e}")
        raise Exception(f"表情包请求失败: {str(e)}")
    except httpx.HTTPStatusError as e:
        logger.error(f"表情包API HTTP错误: {e}")
        raise Exception(f"表情包API返回错误: {e.response.status_code}")
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"表情包数据解析错误: {e}")
        raise Exception(f"表情包数据解析失败: {str(e)}")
    except Exception as e:
        logger.error(f"获取表情包未知错误: {e}")
        raise


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    name="随机表情包",
    description="根据关键词随机获取一张表情包图片URL",
)
async def get_random_emoji(_ctx: AgentCtx, keyword: str) -> str:
    """根据关键词随机获取一张表情包图片URL

    Args:
        keyword: 要搜索的表情包关键词

    Returns:
        str: 随机的表情包图片URL

    Example:
        get_random_emoji("开心")
    """
    try:
        # 获取多个结果随机选择一张
        emoji_list = await get_emoji_pack(keyword, limit=min(10, config.DEFAULT_LIMIT))
        if not emoji_list:
            raise Exception("未找到匹配的表情包")

        return random.choice(emoji_list)
    except Exception as e:
        logger.error(f"获取随机表情包失败: {e}")
        raise Exception(f"获取随机表情包失败: {str(e)}")


@plugin.mount_cleanup_method()
async def clean_up():
    """清理插件资源"""
    # 如有必要，在此实现清理资源的逻辑
    logger.info("表情包获取插件资源已清理")
