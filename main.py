import string
import random
from fastapi.responses import RedirectResponse
from fastapi import FastAPI, Request, Response
import aioredis
from starlette import status
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()


class Redis:
    def __init__(self, url):
        self.url = url
        self.redis = None

    async def connect(self):
        self.redis = await aioredis.from_url(self.url)

    async def close(self):
        await self.redis.close()


r = Redis("redis://localhost:6379")


@app.on_event("startup")
async def startup():
    await r.connect()


@app.on_event("shutdown")
async def shutdown():
    await r.close()


@app.get("/")
async def read_root(request: Request):
    user_agent = request.headers["user-agent"]
    return {"User-Agent": user_agent}


def generate_short_code(length=6):
    chars = string.digits + string.ascii_letters
    return ''.join([random.choice(chars) for _ in range(length)])


async def check_key_exists(key: str):
    exists = await r.redis.exists(key)
    return exists


@app.post("/shorten")
async def shorten_url(url: str):
    # 生成短链接码
    exists = await r.redis.hexists('dl', url)
    if exists:
        short_url = await r.redis.hget('dl', url)
        short_url = short_url.decode()
    else:
        short_url = generate_short_code()
        exists = await r.redis.hexists('dl', url)
        while exists == 1:
            short_url = generate_short_code()
    # 存储短链接和原始URL到Redis数据库
    print(short_url)
    print(url)
    await r.redis.hset('dl', short_url, url)
    await r.redis.hset('dl', url, short_url)
    # 返回生成的短链接
    short_url = f"http://127.0.0.1:8000/u/{short_url}"
    return {"short_url": short_url}


@app.get("/u/{url}", response_class=RedirectResponse, status_code=302)
async def short2long(url: str):
    long_url = await r.redis.hget('dl', url)
    long_url = long_url.decode()
    print(long_url)
    return long_url


@app.get("/pydantic", response_class=RedirectResponse, status_code=302)
async def redirect_pydantic():
    return "https://pydantic-docs.helpmanual.io/"


if __name__ == "__main__":
    import uvicorn

    # 启动服务，注意APP前面的文件名称
    uvicorn.run(app='main:app', host="127.0.0.1", port=8000, reload=True)
