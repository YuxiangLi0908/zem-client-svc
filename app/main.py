from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.router import api_router


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Your API",
        version="1.0.0",
        description="API description",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method.setdefault("security", []).append({"BearerAuth": []})
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app = FastAPI()

# 添加请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"[DEBUG] 收到请求: {request.method} {request.url.path}")
    print(f"[DEBUG] 完整URL: {request.url}")
    print(f"[DEBUG] Headers: {dict(request.headers)}")
    try:
        response = await call_next(request)
        print(f"[DEBUG] 响应状态码: {response.status_code}")
        return response
    except Exception as e:
        print(f"[DEBUG] 请求处理出错: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.add_middleware(GZipMiddleware)
app.include_router(api_router)

app.openapi = custom_openapi

# 启动时打印所有路由
print("="*60)
print("[DEBUG] 服务启动，注册的路由列表:")
for route in app.routes:
    if hasattr(route, 'methods') and hasattr(route, 'path'):
        methods = ', '.join(route.methods)
        print(f"[DEBUG]   {methods:15} -> {route.path}")
print("="*60)
