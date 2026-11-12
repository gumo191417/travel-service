import asyncio

from httpx import AsyncClient

# 全局异步 HTTP 客户端实例
http_client: AsyncClient | None = None


def init_http_client():
    """
    初始化异步 HTTP 客户端（同步函数，启动阶段调用一次）
    """
    global http_client
    # 项目内统一发起 HTTP 请求
    http_client = AsyncClient()


async def close_http_client():
    """
    优雅关闭异步 HTTP 客户端（停止时调用）
    """
    # 已初始化才执行关闭
    if http_client:
        await http_client.aclose()


if __name__ == '__main__':
    init_http_client()

    async def test():
        response = await http_client.get(
            'http://localhost:18081/users/u1001/orders'
        )
        print(response.json()['data']['orders'])
        await close_http_client()

    asyncio.run(test())